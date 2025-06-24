import argparse
import io
import queue
from threading import Condition
from multiprocessing import Process, Pipe
from threading import Thread
import logging
import os
import time

import cv2
import numpy as np
from aiohttp import web, MultipartWriter
from PIL import Image

import aravis

logging.basicConfig()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("server")
log_level = getattr(logging, log_level)
logger.setLevel(log_level)


class StreamHandler:

    def __init__(self, cam):
        self._cam = cam

    async def __call__(self, request):
        my_boundary = 'image-boundary'
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'multipart/x-mixed-replace;boundary={}'.format(my_boundary)
            }
        )
        await response.prepare(request)
        while True:
            frame = await self._cam.get_frame()
            #time.sleep(1/30)
            with MultipartWriter('image/jpeg', boundary=my_boundary) as mpwriter:
                mpwriter.append(frame, {
                    'Content-Type': 'image/jpeg'
                })
                try:
                    await mpwriter.write(response, close_boundary=False)
                except ConnectionResetError :
                    logger.warning("Client connection closed")
                    break
            await response.write(b"\r\n")

class cameraManager:
    def __init__(self, idx, irFramePipe, irFrameRequest, width, height, camScale:int = 1):
        self._idx = idx
        
        self.scale = camScale
        self.width = width
        self.height = height
        self.irFramePipe = irFramePipe
        self.irFrameRequest = irFrameRequest

    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):

        self.irFrameRequest.send(None)
        irFrame = self.irFramePipe.recv()
        irFrame = np.asarray(irFrame)
        if self.scale != 1:
            irFrame = cv2.resize(irFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)
        outputFrame = cv2.imencode('.jpg', irFrame)[1]
        

        return outputFrame.tobytes()
    
    def stop(self):
        '''
        dummy method
        '''
        pass



class MjpegServer:

    def __init__(self, cameras:cameraManager, host='0.0.0.0', port=8080):
        self._port = port
        self._host = host
        self._app = web.Application()
        self._cam_routes = []
        self._viewfinder = cameras

    def start(self):
        self._app.router.add_route("GET", "/", StreamHandler(self._viewfinder))
        web.run_app(self._app, host=self._host, port=self._port)

    def stop(self):
        '''
        dummy method
        actions to be take on closing can be added here
        '''
        pass

def irFrameGen(irFrameIn, irFrameRequest,dims):
    
    try:
        i = 0
        for buf in aravis.ir_buffer_streamer():
            i += 1
            #if i%2 == 0:
            timeStart = time.monotonic_ns()
            # This will run forever, or until you break 
            if buf:
                img = Image.frombytes('L', (dims[0], dims[1]), bytes(buf))
                if irFrameRequest.poll():
                    irFrameIn.send(img)
                    irFrameRequest.recv()
                #print(type(img))
                # if irFrameQueue.full():
                #     #print("Queue Cleared")
                #     irFrameQueue.queue.clear()
                
                # irFrameQueue.put(img)
            timeEnd = time.monotonic_ns()
            #print(timeEnd-timeStart)
            
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")
        


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--scale", 
        default="1",
        type=float,
        help="Webpage viewfinder scale"
    )
    parser.add_argument(
        "--port",
        default=8080,
        type=int,
        help="Port at which server is available on"
    )
    args = parser.parse_args()

    frameRate = 30
    cam_width = 640
    cam_height = 480
    irFrameQueue = queue.LifoQueue(maxsize=4096)
    irFrameOut, irFrameIn = Pipe()
    irRequestOut, irRequestIn = Pipe()
    irProcess = Process(target=irFrameGen, args=(irFrameIn, irRequestOut, (cam_width, cam_height) ), daemon=True) 
    
    cameras = cameraManager(0, irFrameOut, irRequestIn, height=cam_height, width=cam_width, camScale=int(1/args.scale))
    server = MjpegServer(cameras=cameras, port=args.port)

    try:
        irProcess.start()
        server.start()
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")
    finally:
        irProcess.join()
        server.stop()
        cameras.stop()