import numpy as np
import cv2
import aravis
from PIL import Image
import time
from datetime import datetime, timedelta
import subprocess
import sys
import os
from queue import Queue

IP_ADDR   = "169.254.100.1/16"
IFACE     = "eth0"

def configure_interface(addr: str = IP_ADDR, iface: str = IFACE) -> None:
    """Add a link-local address and bring the interface up if needed."""
    # 1. Need CAP_NET_ADMIN privileges → easiest path: run script with sudo
    if os.geteuid() != 0:
        sys.exit("[ERROR] Please run this script with sudo (needs NET_ADMIN)")

    # 2. Is the address already assigned?
    has_ip = subprocess.run(
        ["ip", "-4", "-o", "addr", "show", "dev", iface],
        capture_output=True, text=True, check=False
    )
    if addr.split("/")[0] in has_ip.stdout:
        print(f"[INFO] {iface} already has {addr}")
    else:
        print(f"[INFO] Adding {addr} to {iface}")
        subprocess.run(
            ["ip", "addr", "add", addr, "dev", iface],
            check=True
        )

    # 3. Make sure the link is up
    subprocess.run(["ip", "link", "set", "dev", iface, "up"], check=True)

# Define text properties

org = (25, 25)  # Bottom-left corner of text
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale = 0.5
color = (0, 0, 0)  # Black color (BGR format)
thickness = 2

irDataQueue = Queue()

def irRecord(record_time:int, videoLocation:str, framerate:int = 60):
    starttime = datetime.now()
    width = 640
    height = 480

    fourcc = cv2.VideoWriter_fourcc('F', 'F', 'V', '1')
    video_writer = cv2.VideoWriter(
        filename=videoLocation, 
        fourcc=fourcc, 
        fps=framerate, 
        frameSize=(width, height),
        apiPreference=cv2.CAP_FFMPEG, # Explicitly use FFmpeg backend
        params=[cv2.VIDEOWRITER_PROP_DEPTH, cv2.CV_8U,
                cv2.VIDEOWRITER_PROP_IS_COLOR, 0]
        )

    i = 0
    for array in aravis.ir_buffer_streamer(raw=False):
        pass
        # irDataQueue.put(array)
        i += 1
        if isinstance(array, np.ndarray):
            text = datetime.now().strftime('%H:%M:%S')
            cv2.putText(array, text, org, font, font_scale, color, thickness, cv2.LINE_AA)
            video_writer.write(array)
        
        
        if (datetime.now() - starttime).seconds >= record_time:
            print(i)
            break
        


    video_writer.release()
    print(f"Video '{videoLocation}' created successfully!")

if __name__ == "__main__":
    configure_interface()
    irRecord(300, "test.avi")
    pass