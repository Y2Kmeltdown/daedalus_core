import aravis
import cv2
import numpy as np

import io
from PIL import Image
width = 640
height = 480

try:
    buffer = aravis.get_camera_buffer()
    img = Image.frombytes('L', (width, height), bytes(buffer))
    img = img.save("test.jpg")
except Exception as e:
    print(f"Error: {e}") 