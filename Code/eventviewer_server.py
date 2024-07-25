import argparse
import cv2
import asyncio
import numpy as np
import threading
import queue
import logging
import os
import aiohttp
from aiohttp import web, MultipartWriter
import neuromorphic_drivers as nd

#TODO fix colour map of event viewer
#TODO increase integration time for frames (not really necessary anymore)
#TODO shrink encoded array using CV2 resize and update clear function to match shrunk size
#TODO make the program exitable (Ask Alex)
#TODO related to previous Item on exit evk3 is no longer discoverable by docker container until removing the docker container and replugging the evk 3. Investigate issue (Ask Alex)

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

    def __init__(self, host='0.0.0.0', port=8080):
        self._port = port
        self._host = host
        self._app = web.Application()
        self._cam_routes = []

    async def root_handler(self, request):
        # TO-DO : load page with links
        text = 'Available streams:\n\n'
        for route in self._cam_routes:
            text += f"{route} \n"
        return aiohttp.web.Response(text=text)

    def add_stream(self, route, cam):
        route = f"/{route}"
        self._cam_routes.append(route)
        assert hasattr(cam, 'get_frame'), "arg 'cam' should have a 'get_frame' method"
        self._app.router.add_route("GET", f"{route}", StreamHandler(cam))

    def start(self):
        self._app.router.add_route("GET", "/", self.root_handler)
        web.run_app(self._app, host=self._host, port=self._port)

    def stop(self):
        '''
        dummy method
        actions to be take on closing can be added here
        '''
        pass

configuration = nd.prophesee_evk4.Configuration(
    biases=nd.prophesee_evk4.Biases(
        diff_off=102,  # default: 102
        diff_on=73,  # default: 73
    )
)

class Camera:
    def __init__(self, idx, cam_dim:tuple, eventQueue:queue.Queue):
        self._idx = idx
        self.width = cam_dim[0]
        self.height = cam_dim[1]
        self.clear_frame()
        self.events = eventQueue

    @property
    def identifier(self):
        return self._idx

    async def get_frame(self):
        packet = self.events.get()
        self.events.queue.clear()
        self.frame[
            packet["dvs_events"]["y"],
            packet["dvs_events"]["x"],
            ] = 255
        #testframe = cv2.resize(self.frame, dsize=(54, 140), interpolation=cv2.INTER_CUBIC)
        frameout = cv2.imencode('.jpg', np.flip(self.frame, 0))[1]
        self.clear_frame()
        await asyncio.sleep(1 / 25)
        return frameout.tobytes()
    
    def stop(self):
        '''
        dummy method
        '''
        pass

    def clear_frame(self):
        self.frame = np.zeros(
        (self.height, self.width),
        dtype=np.float32,
        )

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("serial", help="Camera serial number (for example 00050423)")
parser.add_argument(
    "--route",
    default="cam0",
    type=str,
    help="Path to stream directory"
)
parser.add_argument(
    "--port",
    default=8000,
    type=int,
    help="Port at which server is available on"
)
args = parser.parse_args()

with nd.open(serial=args.serial) as device:
    cam_width = device.properties().width
    cam_height = device.properties().height

def getEvents(out_q):
    with nd.open(serial=args.serial) as device:#configuration=configuration
        print(f"Successfully started EVK4 {args.serial}")

        for status, packet in device:

            out_q.put(packet)
            
eventQueue = queue.LifoQueue()
eventProcess = threading.Thread(target=getEvents, args=(eventQueue, ))   
eventProcess.daemon=True  
server = MjpegServer(port=args.port)
cam = Camera(0, (cam_width, cam_height), eventQueue)
server.add_stream(args.route, cam)
eventProcess.start()

try:
    server.start()
finally:
    server.stop()
    cam.stop()



        
        

            