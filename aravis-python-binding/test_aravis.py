import aravis
import cv2
import numpy as np

import io
from PIL import Image
from multiprocessing import Process, Pipe
from queue import LifoQueue
import time

width = 640
height = 480

try:
    # buffer = aravis.get_camera_buffer()
    # print(buffer)
    # img = Image.frombytes('L', (width, height), bytes(buffer))
    # img = img.save(f"data/test.jpg")
    
    # buffers = aravis.get_camera_buffers(60)
    # for i, buffer in enumerate(buffers):
    #     print(len(buffer))
    #     img = Image.frombytes('L', (width, height), bytes(buffer))
    #     img = img.save(f"data/test{i}.jpg")

    i = 0
    frameStart = time.monotonic_ns()
    totalStart = time.monotonic_ns()
    computeTime = ""
    for buf in aravis.ir_buffer_streamer():
        frameNo = f"Frame: {i}"
        totalEnd = time.monotonic_ns()
        totalTime = f"Total Time:{totalEnd-totalStart}"
        totalStart = time.monotonic_ns()
        frameEnd = time.monotonic_ns()
        frameTime = f"Frame Timing:{frameEnd-frameStart}"
        print(f"{frameNo}\n{frameTime}\n{computeTime}\n{totalTime}\n")
        computeStart = time.monotonic_ns()
        i += 1
        if buf:
            img = Image.frombytes('L', (width, height), bytes(buf))
        
        if i % 2:
            time.sleep(0.001)
            
        computeEnd = time.monotonic_ns()
        computeTime = f"Compute Time:{computeEnd-computeStart}"
        
        frameStart = time.monotonic_ns()

except Exception as e:
    print(f"Error: {e}") 