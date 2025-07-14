import argparse
import io
from threading import Condition, Thread
from multiprocessing import Process, Pipe, Lock
import logging
import os
import time
import queue

from PIL import Image
import cv2
import numpy as np
from aiohttp import web, MultipartWriter
import neuromorphic_drivers as nd
import aravis

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

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
    def __init__(self, idx, width, height, camScale:int = 1):
        self._idx = idx
        self.scale = camScale
        self.width = width
        self.height = height

        # self.eventFramePipe = event_frame_out
        # self.eventFrameRequest = eventFrameRequest

        # self.irFramePipe = irFramePipe
        # self.irFrameRequest = irFrameRequest

    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):
        global output_ir_frame
        global output_event_frame

        #self.eventFrameRequest.send(None)
        #eventFrame = self.eventFramePipe.recv()
        eventFrame = output_event_frame

        #self.irFrameRequest.send(None)
        #irFrame = self.irFramePipe.recv()
        irFrame = np.asarray(output_ir_frame)

        with output.condition:
            output.condition.wait()
            convBytes = output.frame
            convFrame = cv2.imdecode(np.frombuffer(convBytes,np.uint8), cv2.IMREAD_COLOR)
            
        if self.scale != 1:
            eventFrame = cv2.resize(eventFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)
            convFrame = cv2.resize(convFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)
            irFrame = cv2.resize(irFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)
        
        flippedEventFrame = np.flip(eventFrame, 0)
        rgbEventFrame = np.stack((flippedEventFrame,)*3, axis=-1)
        rgbIRFrame = np.stack((irFrame,)*3, axis=-1)
        
        mergedFrame = np.concatenate((rgbEventFrame, convFrame, rgbIRFrame), 0)

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
        
def eventProducer(serial, config, dims):
    global output_event_frame
    frame = np.zeros(
        (dims[1], dims[0]),
        dtype=np.float32,
    )+127
    oldTime = time.monotonic_ns()
    with nd.open(serial=serial, configuration=config) as device:
        print(f"Successfully started EVK4 {args.serial}")

        for status, packet in device:
            if packet:
                if "dvs_events" in packet:
                    frame[
                        packet["dvs_events"]["y"],
                        packet["dvs_events"]["x"],
                    ] = packet["dvs_events"]["on"]*255
                    if time.monotonic_ns()-oldTime >= (1/50)*1000000000:
                        with data_lock:
                            output_event_frame = frame
                        
                        # if eventFrameRequest.poll():
                        #     event_frame_in.send(frame)
                        #     eventFrameRequest.recv()

                        frame = np.zeros(
                            (dims[1], dims[0]),
                            dtype=np.float32,
                        )+127
                        oldTime = time.monotonic_ns()
    

def irFrameGen(dims):
    global output_ir_frame
    
    try:
        i = 0
        for buf in aravis.ir_buffer_streamer():
            i += 1
            #if i%2 == 0:
            #timeStart = time.monotonic_ns()
            # This will run forever, or until you break
                
            if buf:
                img = Image.frombytes('L', (dims[0], dims[1]), bytes(buf))

                with data_lock:
                    output_ir_frame = img
                # if irFrameRequest.poll():
                #     irFrameIn.send(img)
                #     irFrameRequest.recv()
            #timeEnd = time.monotonic_ns()
            #print(timeEnd-timeStart)
            
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")

def check_event_camera(serialNumberList):
    evkSerialList = [i.serial for i in nd.list_devices()]
    try:
        serialNumbers = [i for i in evkSerialList if i in serialNumberList]
        return serialNumbers
    except Exception as e:
        print(f"Error during serial number check: {e}", flush=True)
        return None

if __name__ == "__main__":
    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=80,  # default: 102
            diff_on=140,  # default: 73
        )
    )

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--serial", 
        default="",
        help="Camera serial number list. Will start recording data from all specified cameras if they are connected. If  (for example 00050423 00051505 00051503)",
        nargs="+",
        type=str
    )
    parser.add_argument(
        "--scale", 
        default="0.5",
        type=float,
        help="Webpage viewfinder scale"
    )
    parser.add_argument(
        "--picam", 
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

    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=102,  # default: 102
            diff_on=73,    # default: 73
        )
    )

    if args.serial == "":
        evkSerialList = [i.serial for i in nd.list_devices()]
    else:
        evkSerialList = check_event_camera(args.serial)
    
    if evkSerialList:
        pass
    else:
        print("[INFO] No Event Cameras connected to system.", flush=True)

    data_lock = Lock()
    output_event_frame = None
    output_ir_frame = None

    picam2 = Picamera2(int(args.picam))
    picam2.configure(picam2.create_video_configuration(main={"size": (1280, 960)}))
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))

    with nd.open(serial=evkSerialList[0]) as device:
        cam_width = device.properties().width
        cam_height = device.properties().height
    event_frame_output, event_frame_input = Pipe()
    event_frame_request_output, event_frame_request_input = Pipe()
    eventProcess = Process(target=eventProducer, args=(evkSerialList[0], configuration, (cam_width, cam_height)), daemon=True)

    ir_cam_width = 640
    ir_cam_height = 480
    irFrameOut, irFrameIn = Pipe()
    ir_frame_request_output, ir_frame_request_input = Pipe()
    irProcess = Process(target=irFrameGen, args=((ir_cam_width, ir_cam_height), ), daemon=True) 
                
    cameras = cameraManager(
        idx=0, 
        height=cam_height, 
        width=cam_width, 
        camScale=int(1/args.scale)
        )
    
    server = MjpegServer(cameras=cameras, port=args.port)

    try:
        irProcess.start()
        eventProcess.start()
        server.start()
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")
    finally:
        irProcess.join()
        eventProcess.join()
        server.stop()
        cameras.stop()
        picam2.stop_recording()