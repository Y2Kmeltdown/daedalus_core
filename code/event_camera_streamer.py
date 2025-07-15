import argparse
import cv2
import asyncio
import numpy as np
import logging
import os
import time
from multiprocessing import Process, Pipe, Lock, Array, shared_memory
# import signal

from aiohttp import web, MultipartWriter
import neuromorphic_drivers as nd

from multiprocessing import Process, Pipe

#TODO fix colour map of event viewer
#TODO increase integration time for frames (not really necessary anymore)
#TODO make the program exitable (Ask Alex)
#TODO related to previous Item on exit evk3 is no longer discoverable by docker container until removing the docker container and replugging the evk 3. Investigate issue (Ask Alex)

logging.basicConfig()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("server")
log_level = getattr(logging, log_level)
logger.setLevel(log_level)

data_lock = Lock()

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

class Camera:
    def __init__(self, idx, shm_event_data, width, height, camScale:int = 1):
        self._idx = idx
        
        self.scale = camScale
        self.width = width
        self.height = height
        self.eventMemory = shm_event_data

    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):
        
        eventFrame = np.frombuffer(self.eventMemory.buf[:], dtype=np.uint8)
        eventFrame = eventFrame.reshape((self.height, self.width))
        if self.scale != 1:
            eventFrame = cv2.resize(eventFrame, dsize=(self.width//self.scale, self.height//self.scale), interpolation=cv2.INTER_CUBIC)
        frameout = cv2.imencode('.jpg', np.flip(eventFrame, 0))[1]
        await asyncio.sleep(1 / 25)
        return frameout.tobytes()
    
    def stop(self):
        '''
        dummy method
        '''
        pass

    

class MjpegServer:

    def __init__(self, cam:Camera, host='0.0.0.0', port=8080):
        self._port = port
        self._host = host
        self._app = web.Application()
        self._cam_routes = []
        self._cam = cam

    def start(self):
        self._app.router.add_route("GET", "/", StreamHandler(self._cam))
        web.run_app(self._app, host=self._host, port=self._port)

    def stop(self):
        '''
        dummy method
        actions to be take on closing can be added here
        '''
        pass

def eventProducer(serial, config, dims, event_shared_memory):
    frame = np.zeros(
        (dims[1], dims[0]),
        dtype=np.uint8,
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
                            event_shared_memory.buf[:] = frame.tobytes()
                        frame = np.zeros(
                            (dims[1], dims[0]),
                            dtype=np.uint8,
                        )+127
                        oldTime = time.monotonic_ns()
    
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
            diff_off=102,  # default: 102
            diff_on=73,  # default: 73
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

    with nd.open(serial=evkSerialList[0]) as device:
        cam_width = device.properties().width
        cam_height = device.properties().height
    shm_event_data = shared_memory.SharedMemory(create=True, size=cam_width*cam_height)
    eventProcess = Process(target=eventProducer, args=(evkSerialList[0], configuration, (cam_width, cam_height), shm_event_data), daemon=True)
    
    cam = Camera(0, shm_event_data, height=cam_height, width=cam_width, camScale=1)
    server = MjpegServer(cam=cam, port=args.port)

    try:
        eventProcess.start()
        server.start()
    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")
    finally:
        eventProcess.join()
        shm_event_data.close()
        shm_event_data.unlink()
        server.stop()
        cam.stop()