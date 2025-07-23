import argparse
from multiprocessing import Process, Lock, shared_memory
import logging
import os

import cv2
import numpy as np
from aiohttp import web, MultipartWriter

import aravis
import daedalus_utils

data_lock = Lock()


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
    def __init__(self, idx, ir_memory, width, height, camScale:int = 1):
        self._idx = idx
        
        self.scale = camScale
        self.width = width
        self.height = height
        self.irMemory = ir_memory
        

    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):
        irFrame = np.frombuffer(self.irMemory.buf[:], dtype=np.uint8)
        irFrame = irFrame.reshape((self.height, self.width))
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

def irFrameGen(ir_shared_memory):
    try:
        for buffer in aravis.ir_buffer_streamer():
            # This will run forever, or until you break
            if buffer:
                with data_lock:
                    ir_shared_memory.buf[:] = buffer
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

    ir_cam_width = 640
    ir_cam_height = 480
    IP_ADDR = "169.254.100.1/16"
    IFACE = "eth0"
    daedalus_utils.configure_interface(addr=IP_ADDR, iface=IFACE)
    shm_ir_data = shared_memory.SharedMemory(create=True, size=ir_cam_width*ir_cam_height)
    irProcess = Process(target=irFrameGen, args=(shm_ir_data, ), daemon=True) 
    
    cameras = cameraManager(0, shm_ir_data, height=ir_cam_height, width=ir_cam_width, camScale=int(1/args.scale))
    server = MjpegServer(cameras=cameras, port=args.port)

    try:
        irProcess.start()
        server.start()
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")
    finally:
        shm_ir_data.close()
        shm_ir_data.unlink()
        irProcess.join()
        server.stop()
        cameras.stop()