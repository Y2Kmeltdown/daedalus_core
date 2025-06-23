import numpy as np
import cv2
import aravis
from PIL import Image
import time

def irRecord(record_time:int, videoLocation:str):
    width = 640
    height = 480


    buffers = aravis.get_camera_buffers(record_time*60)

    
    first_img = Image.frombytes('L', (width, height), bytes(buffers[0]))
    first_frame = np.asarray(first_img)
    height, width = first_frame.shape


    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    video = cv2.VideoWriter(videoLocation, fourcc, 60, (width, height))

    for i, buffer in enumerate(buffers):
        img = Image.frombytes('L', (width, height), bytes(buffer))
        np_frame = np.asarray(img)
        frame = cv2.cvtColor(np_frame, cv2.COLOR_GRAY2BGR)
        video.write(frame)

    video.release()
    print(f"Video '{videoLocation}' created successfully!")

if __name__ == "__main__":
    irRecord(5, "test.mp4")
    pass