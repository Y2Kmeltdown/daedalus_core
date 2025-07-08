import time
import datetime
import json
import argparse
import sys
import io

from picamera2 import Picamera2
from libcamera import controls

import daedalus_utils

def check_request_timestamp(request, check_time):
    md = request.get_metadata()
    exposure_start_time = md['SensorTimestamp'] - 1000 * md['ExposureTime']
    if exposure_start_time < check_time:
        print("ERROR: request captured too early by", check_time - exposure_start_time, "nanoseconds")


def cameraControls(camera: Picamera2, jsonConfig: str):
    if jsonConfig is not None:
        camera.set_controls({"AfMode": controls.AfModeEnum.Manual})
        camera.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
        with open(jsonConfig) as f:
            settings = json.load(f)
            print(settings, flush=True)
            for setting, value in settings.items():
                camera.set_controls({setting: value})

def cameraHandler(camID, piCamDataHandler:daedalus_utils.data_handler, config):
    picam = Picamera2(camID)
    config = picam.create_still_configuration()
    picam.configure(config)

    print(f"[INFO] {piCamDataHandler.sensorName} Starting snapshots", flush=True)
    picam.start()
    time.sleep(1)
    #cameraControls(picam, config)
    time.sleep(2)
    while True:
        try:
            data = io.BytesIO()
            timestr = time.strftime("%Y%m%d-%H%M%S")
            ct = datetime.datetime.now()
            check_time = time.monotonic_ns() + 5e8
            picam.capture_file(data, format='png')

            imgMetadata = {
                "filename": piCamDataHandler.file_name,
                "timestamp": str(ct),
                "timestamp(ns)": check_time
            }

            data.seek(0)  # Ensure you're at the beginning of the BytesIO object
            chunk_size = 4096  # Define a suitable chunk size
            bytesList = []
            while True:
                chunk = data.read(chunk_size)
                if not chunk:
                    break  # End of data
                bytesList.append(chunk)
                
            piCamDataHandler.write_data(bytesList, now=True)

            

            
        except Exception as e:
            print(f"Error during snapshot capture: {e}", flush=True)

        time.sleep(args.timer)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--camera", 
        default="0",
        help="Camera number (for example 0 or 1)")
    parser.add_argument(
        "--data",
        default="/usr/local/daedalus/data/pi_picture",
        help="Path of the directory where recordings are stored",
        )
    parser.add_argument(
        "--backup",
        default="/mnt/data/pi_picture",  # Default root path for backup
        help="Path of the directory where recordings are backed up",
        )
    parser.add_argument(
        "--timer",
        default=1,
        type=int,
        help="Time in seconds between snapshots"
    )
    parser.add_argument(
        "--socket",
        default=str("/tmp/piImage.sock"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration json for camera properties",
    )
    args = parser.parse_args()

    # picam = Picamera2(int(args.camera))
    # config = picam.create_still_configuration()
    # picam.configure(config)

    # picam.start()
    # time.sleep(1)
    # cameraControls(picam, args.config)
    # time.sleep(2)

    piCamDataHandler = daedalus_utils.data_handler(
        sensorName=f"piCamera{args.camera}",
        extension=".png",
        dataPath=args.data,
        backupPath=args.backup,
        recordingTime=0,
        socketPath=args.socket
    )

    try:
        cameraHandler(
            int(args.camera),
            piCamDataHandler,
            args.config
        )

    except (KeyboardInterrupt, SystemExit):
        print("\nEnding pi_camera_picture_datalogger.py")
        sys.exit(0)

