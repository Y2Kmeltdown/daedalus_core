from posix import times
import aravis
import cv2
import numpy as np

import io
from PIL import Image
width = 640
height = 480
from multiprocessing import Process, Pipe
from queue import LifoQueue

import time
frame_output, frame_input = Pipe()
frameQueue = LifoQueue(maxsize=60)

try:
    # buffer = aravis.get_camera_buffer()
    #print(buffer)
    #img = Image.frombytes('L', (width, height), bytes(buffer))
    #img = img.save(f"data/test.jpg")
    
    # buffers = aravis.get_camera_buffers(60)
    # for i, buffer in enumerate(buffers):
    #     print(len(buffer))
    #     img = Image.frombytes('L', (width, height), bytes(buffer))
    #     img = img.save(f"data/test{i}.jpg")

    i = 0
    frameStart = time.monotonic_ns()
    for buf in aravis.ir_buffer_streamer(framerate = 30):
        i += 1
        print(f"Frame {i}")
        computeStart = time.monotonic_ns()
        
        
        #img.save(f"data/test{i}.jpg")
        #print(len(buf))
        #if i%2 == 0:

        #time.sleep(1/15)
        
        if buf:
            img = Image.frombytes('L', (width, height), bytes(buf))
        computeEnd= time.monotonic_ns()
        frameEnd = time.monotonic_ns()
        print(f"Frame Timing:{frameEnd-frameStart}")
        print(f"Compute Timing:{computeEnd-computeStart}")


        frameStart = time.monotonic_ns()
        #time.sleep(2)
        #print(timeEnd-timeStart)
        # if i == 30:
        #     break

    
except Exception as e:
    print(f"Error: {e}") 