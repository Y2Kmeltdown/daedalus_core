import aravis
import cv2
import numpy as np

import io
from PIL import Image
width = 640
height = 480

import time

try:
    # buffer = aravis.get_camera_buffer()
    # start = time.monotonic_ns()
    # buffers = aravis.get_camera_buffers(10)
    # end = time.monotonic_ns()
    # print(f"Time Taken: {end-start}")
    # print(type(buffers))
    # print(len(buffers))
    # print(len(buffers[0]))
    # for i, buffer in enumerate(buffers):
    #     img = Image.frombytes('L', (width, height), bytes(buffer))
    #     img = img.save(f"test{i}.jpg")
    i = 0
    for buf in aravis.camera_buffer_stream():
        # This will run forever, or until you break
        i += 1
        img = Image.frombytes('L', (width, height), bytes(buf))
        img = img.save(f"data/test{i}.jpg")
        time.sleep(1/10)
        
        if i == 30:
            break  # You control when to stop!
except Exception as e:
    print(f"Error: {e}") 