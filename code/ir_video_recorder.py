import numpy as np
import argparse
import cv2
import aravis
import time
import subprocess
import sys
import os
from queue import Queue
from threading import Thread
from datetime import datetime

import daedalus_utils

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



def irDataSaver(videoLocation:str, dataQueue:Queue):
    starttime = time.monotonic_ns()
    global data_done
    width = 640
    height = 480
    framerate = 60

    fourcc = cv2.VideoWriter_fourcc('F', 'F', 'V', '1')
    video_writer = cv2.VideoWriter(
        filename=videoLocation, 
        fourcc=fourcc, 
        fps=framerate, 
        frameSize=(width, height),
        apiPreference=cv2.CAP_FFMPEG, # Explicitly use FFmpeg backend
        params=[cv2.VIDEOWRITER_PROP_DEPTH, cv2.CV_16U,
                cv2.VIDEOWRITER_PROP_IS_COLOR, 0]
        )
    
    while True:
        frame = dataQueue.get()
        video_writer.write(frame)
        if data_done and dataQueue.empty():
            break

    endTime = time.monotonic_ns()

    video_writer.release()
    print(f"[INFO] Video '{videoLocation}' created successfully!", flush=True)
    

def irRecord(record_time:int, dataFile:str, backupFile:str):
    print("[INFO] IR Camera Recorder starting", flush=True)
    global data_done

    # Define text properties

    org = (25, 25)  # Bottom-left corner of text
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    color = (0, 0, 0)  # Black color (BGR format)
    thickness = 1


    data_done = False
    starttime = datetime.now()
    dataQueue = Queue()
    dataThread = Thread(target=irDataSaver, args=(dataFile, dataQueue), daemon=True)
    dataThread.start()

    backupQueue = Queue()
    backupThread = Thread(target=irDataSaver, args=(backupFile , backupQueue), daemon=True)
    backupThread.start()
    
    for array in aravis.ir_buffer_streamer(raw=True, lowFPS=True):

        if isinstance(array, np.ndarray):
            text = datetime.now().strftime('%H:%M:%S')
            cv2.putText(array, text, org, font, font_scale, color, thickness, cv2.LINE_AA)
            dataQueue.put(array)
            backupQueue.put(array)

        if (datetime.now() - starttime).seconds >= record_time:
            data_done = True
            break

    dataThread.join()
    backupThread.join()


            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--serial", 
        default="",
        help="Camera serial number list. Will start recording data from all specified cameras if they are connected (for example 00050423 00051505 00051503).\nIf none are specified the first available camera will be used.",
        nargs="+",
        type=str
    )
    
    parser.add_argument(
        "--data",
        default="/home/daedalus/daedalus_core/data",
        help="Path of the directory where recordings are stored",
    )
    parser.add_argument(
        "--backup",
        default=str("/mnt/data"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--record_time",
        default=300,
        type=int,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()

    irDataHandler = daedalus_utils.data_handler(
        sensorName="ir_video",
        extension=".avi",
        dataPath=args.data,
        backupPath=args.backup,
        recordingTime=args.record_time
    )

    index = 0
    while True:
        configure_interface()
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        index += 1
        file_name = f"{args.data}/ir_video_{current_time}_{index}.avi"
        backup_name = f"{args.backup}/ir_video_{current_time}_{index}.avi"
        irRecord(args.record_time, file_name, backup_name)


