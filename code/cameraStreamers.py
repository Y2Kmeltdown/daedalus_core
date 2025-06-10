import argparse
import io
import cv2
import asyncio
import numpy as np
import threading
from threading import Condition
import queue
import logging
import os
import time

from aiohttp import web, MultipartWriter
import neuromorphic_drivers as nd

from multiprocessing import Process, Pipe

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

from PIL import Image

logging.basicConfig()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("server")
log_level = getattr(logging, log_level)
logger.setLevel(log_level)

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

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
    def __init__(self, idx, p_output, width, height, camScale:int = 1):
        self._idx = idx
        
        self.scale = camScale
        self.width = width
        self.height = height
        self.framepipe = p_output

    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):
        eventFrame = self.framepipe.recv()
        if self.scale != 1:
            eventFrame = cv2.resize(eventFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)

        with output.condition:
            output.condition.wait()
            convBytes = output.frame
            convFrame = cv2.imdecode(np.frombuffer(convBytes,np.uint8), cv2.IMREAD_COLOR)
            convFrame = cv2.resize(convFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)
        
        flippedEventFrame = np.flip(eventFrame, 0)
        rgbEventFrame = np.stack((flippedEventFrame,)*3, axis=-1)
        
        mergedFrame = np.concatenate((rgbEventFrame, convFrame), 0)

        outputFrame = cv2.imencode('.jpg', mergedFrame)[1]

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

def eventProducer(p_input):
        configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=102,  # default: 102
            diff_on=73,  # default: 73
            )
        )
        with nd.open(serial=args.serial, configuration=configuration) as device:
            print(f"Successfully started EVK4 {args.serial}")

            for status, packet in device:
                if packet:
                    p_input.send(packet)
                

def eventAccumulator(event_out, frame_in, dims):
    frame = np.zeros(
        (dims[1], dims[0]),
        dtype=np.float32,
    )+127
    oldTime = time.monotonic_ns()
    # try:
    while True:
        packet = event_out.recv()
        frame[
            packet["dvs_events"]["y"],
            packet["dvs_events"]["x"],
        ] = packet["dvs_events"]["on"]*255
        if time.monotonic_ns()-oldTime >= (1/50)*1000000000:
            frame_in.send(frame)
            frame = np.zeros(
                (dims[1], dims[0]),
                dtype=np.float32,
            )+127
            oldTime = time.monotonic_ns()

    

if __name__ == "__main__":
    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=102,  # default: 102
            diff_on=73,  # default: 73
        )
    )

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--serial", 
        default="00051501",
        help="Camera serial number (for example 00050423)"
    )
    parser.add_argument(
        "--camera", 
        default=0,
        help="Camera number (for example 0 or 1)"
    )
    parser.add_argument(
        "--port",
        default=8080,
        type=int,
        help="Port at which server is available on"
    )
    args = parser.parse_args()

    picam2 = Picamera2(int(args.camera))
    picam2.configure(picam2.create_video_configuration(main={"size": (1280, 960)}))
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))

    with nd.open(serial=args.serial) as device:
        cam_width = device.properties().width
        cam_height = device.properties().height
                
    event_output, event_input = Pipe()
    frame_output, frame_input = Pipe()

    eventProcess = Process(target=eventProducer, args=(event_input, ), daemon=True)   
    frameProcess = Process(target=eventAccumulator, args=(event_output, frame_input,(cam_width, cam_height) ), daemon=True) 
    
    cameras = cameraManager(0, frame_output, height=cam_height, width=cam_width, camScale=1)
    server = MjpegServer(cameras=cameras, port=args.port)

    try:
        eventProcess.start()
        frameProcess.start()
        server.start()
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")
    finally:
        eventProcess.join()
        frameProcess.join()
        server.stop()
        cameras.stop()
        picam2.stop_recording()