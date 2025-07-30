import argparse
import io
from threading import Condition
from multiprocessing import Process, Lock, shared_memory
import logging
import os
import time

import cv2
import numpy as np
from aiohttp import web, MultipartWriter
import neuromorphic_drivers as nd
import aravis
import daedalus_utils

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

logging.basicConfig()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("server")
log_level = getattr(logging, log_level)
logger.setLevel(log_level)

data_lock = Lock()

def eventProducer(serial, config, dims, event_shared_memory):
    frame = np.zeros(
        (dims[1], dims[0]),
        dtype=np.uint8,
    )+127
    oldTime = time.monotonic_ns()
    try:
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
                                event_shared_memory.buf[:] = frame.tobytes()

                            frame = np.zeros(
                                (dims[1], dims[0]),
                                dtype=np.uint8,
                            )+127
                            oldTime = time.monotonic_ns()
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")

def irFrameGen(ir_shared_memory:shared_memory.SharedMemory):
    try:
        for buffer in aravis.ir_buffer_streamer():
            # This will run forever, or until you break
            if buffer:
                with data_lock:
                    ir_shared_memory.buf[:] = buffer
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class cameraManager:
    def __init__(self, idx, eventMemory:shared_memory.SharedMemory, irMemory:shared_memory.SharedMemory, eventCameraShape:tuple, irCameraShape:tuple, piCameraShape:tuple):
        self._idx = idx
        self.eventCameraShape = eventCameraShape
        self.irCameraShape = irCameraShape
        self.piCameraShape = piCameraShape
        self.eventMemory = eventMemory
        self.irMemory = irMemory


    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):
        
        ir_height = self.irCameraShape[0]
        ir_width = self.irCameraShape[1]
        ir_scale = self.irCameraShape[2]
        irFrame = np.frombuffer(self.irMemory.buf[:], dtype=np.uint8)
        irFrame = irFrame.reshape((ir_height, ir_width))
        if ir_scale != 1:
            irFrame = cv2.resize(irFrame, dsize=(ir_width//ir_scale, ir_height//ir_scale), interpolation=cv2.INTER_CUBIC)
        rgbIRFrame = np.stack((irFrame,)*3, axis=-1)


        event_height = self.eventCameraShape[0]
        event_width = self.eventCameraShape[1]
        event_scale = self.eventCameraShape[2]
        eventFrame = np.frombuffer(self.eventMemory.buf[:], dtype=np.uint8)
        eventFrame = eventFrame.reshape((event_height, event_width))
        if event_scale != 1:
            eventFrame = cv2.resize(eventFrame, dsize=(event_width//event_scale, event_height//event_scale), interpolation=cv2.INTER_CUBIC)
        flippedEventFrame = np.flip(eventFrame, 0)
        rgbEventFrame = np.stack((flippedEventFrame,)*3, axis=-1)

        
        pi_height = self.piCameraShape[0]
        pi_width = self.piCameraShape[1]
        pi_scale = self.piCameraShape[2]
        try:
            with piProcess.condition:
                test = piProcess.condition.wait(timeout=5)
                print(test)
                convBytes = piProcess.frame
                convFrame = cv2.imdecode(np.frombuffer(convBytes,np.uint8), cv2.IMREAD_COLOR)
            if pi_scale != 1:
                convFrame = cv2.resize(convFrame, dsize=(pi_width//pi_scale, pi_height//pi_scale), interpolation=cv2.INTER_CUBIC)
        except:
            convFrame = np.zeros((pi_height, pi_width, 3))
            convFrame = cv2.resize(convFrame, dsize=(pi_width//pi_scale, pi_height//pi_scale), interpolation=cv2.INTER_CUBIC)
            
        
        mergedFrame = np.concatenate((rgbEventFrame, convFrame, rgbIRFrame), 0)
        outputFrame = cv2.imencode('.jpg', mergedFrame)[1]
        return outputFrame.tobytes()
    
    def stop(self):
        '''
        dummy method
        '''
        pass

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
        
def check_event_camera(serialNumberList):
    evkSerialList = [i.serial for i in nd.list_devices()]
    try:
        serialNumbers = [i for i in evkSerialList if i in serialNumberList]
        return serialNumbers
    except Exception as e:
        print(f"Error during serial number check: {e}", flush=True)
        return None

if __name__ == "__main__":
    

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
            diff_off=80,  # default: 102
            diff_on=140,  # default: 73
        ),
        rate_limiter=nd.prophesee_evk4.RateLimiter(
            reference_period_us=200,
            maximum_events_per_period=4000
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

    pi_cam_width = 1280
    pi_cam_height = 960
    try:
        picam2 = Picamera2(int(args.picam))
        picam2.configure(picam2.create_video_configuration(main={"size": (pi_cam_width, pi_cam_height)}))
        piProcess = StreamingOutput()
        picam2.start_recording(JpegEncoder(), FileOutput(piProcess))
        piCamShape = (pi_cam_height, pi_cam_width, 2)
    except:
        piCamShape = (pi_cam_height, pi_cam_width, 2)


    event_cam_width = 1280
    event_cam_height = 720
    try:
        with nd.open(serial=evkSerialList[0]) as device:
            event_cam_width = device.properties().width
            event_cam_height = device.properties().height
        shm_event_data = shared_memory.SharedMemory(create=True, size=event_cam_width*event_cam_height)
        eventProcess = Process(target=eventProducer, args=(evkSerialList[0], configuration, (event_cam_width, event_cam_height), shm_event_data), daemon=True)
        eventCamShape = (event_cam_height, event_cam_width, 2)
    except:
        shm_event_data = shared_memory.SharedMemory(create=True, size=event_cam_width*event_cam_height)
        eventCamShape = (event_cam_height, event_cam_width, 2)

    ir_cam_width = 640
    ir_cam_height = 480
    try:
        daedalus_utils.configure_interface()
        shm_ir_data = shared_memory.SharedMemory(create=True, size=ir_cam_width*ir_cam_height)
        irProcess = Process(target=irFrameGen, args=(shm_ir_data, ), daemon=True) 
        irCamShape = (ir_cam_height, ir_cam_width, 1)
    except:
        shm_ir_data = shared_memory.SharedMemory(create=True, size=ir_cam_width*ir_cam_height)
        irCamShape = (ir_cam_height, ir_cam_width, 1)
  
    cameras = cameraManager(
        idx=0, 
        eventMemory=shm_event_data,
        irMemory=shm_ir_data,
        eventCameraShape=eventCamShape,
        piCameraShape=piCamShape,
        irCameraShape=irCamShape
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
        shm_event_data.close()
        shm_ir_data.close()
        shm_event_data.unlink()
        shm_ir_data.unlink()
        picam2.stop_recording()