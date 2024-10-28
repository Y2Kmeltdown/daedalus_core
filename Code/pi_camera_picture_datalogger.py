import time
import datetime
import json
import argparse
from pathlib import Path
from picamera2 import Picamera2
from libcamera import controls
import os

dirname = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("camera", help="Camera number (for example 0 or 1)")
parser.add_argument(
    "--data",
    default=str(dirname / "recordings"),
    help="Path of the directory where recordings are stored",
)
parser.add_argument(
    "--backup",
    default="/mnt/data",  # Default root path for backup
    help="Path of the directory where recordings are backed up",
)
parser.add_argument(
    "--timer",
    default=10,
    type=int,
    help="Time in seconds between snapshots"
)
parser.add_argument(
    "--config",
    type=str,
    help="Path to configuration json for camera properties",
)
args = parser.parse_args()

def check_request_timestamp(request, check_time):
    md = request.get_metadata()
    exposure_start_time = md['SensorTimestamp'] - 1000 * md['ExposureTime']
    if exposure_start_time < check_time:
        print("ERROR: request captured too early by", check_time - exposure_start_time, "nanoseconds")

def save_snapshot(data_path: str, backup_path: str, filename: str, imgMetadata: dict, request):
    # Save to data directory
    try:
        with open(f'{data_path}/{filename}.json', 'w') as f:
            f.write(json.dumps(imgMetadata))
        print(f'Metadata saved to {data_path}/{filename}.json', flush=True)
        request.save('main', f'{data_path}/{filename}.png')
        print(f'Snapshot saved to {data_path}/{filename}.png', flush=True)
    except Exception as e:
        print(f"Error saving to data directory: {e}", flush=True)

    # Save to backup directory if available
    if is_backup_available(backup_path):
        try:
            Path(backup_path).mkdir(parents=True, exist_ok=True)
            with open(f'{backup_path}/{filename}.json', 'w') as f:
                f.write(json.dumps(imgMetadata))
            print(f'Metadata saved to {backup_path}/{filename}.json', flush=True)
            request.save('main', f'{backup_path}/{filename}.png')
            print(f'Snapshot saved to {backup_path}/{filename}.png', flush=True)
        except Exception as e:
            print(f"Error saving to backup directory: {e}", flush=True)
    else:
        print("Backup directory not available. Saving to SD card only.", flush=True)

def snapshot(camera: Picamera2, data_path: str, backup_path: str):
    timestr = time.strftime("%Y%m%d-%H%M%S")
    ct = datetime.datetime.now()
    check_time = time.monotonic_ns() + 5e8
    job = camera.capture_request(flush=check_time, wait=False)

    request = camera.wait(job)
    check_request_timestamp(request, check_time)

    imgMetadata = {
        "filename": f"cam_{camera.camera_idx}_image_{timestr}.png",
        "timestamp": str(ct),
        "timestamp(ns)": check_time
    }

    # Save snapshot to both data and backup, passing the request object
    save_snapshot(data_path, backup_path, f"cam_{camera.camera_idx}_image_{timestr}", imgMetadata, request)
    request.release()

def cameraControls(camera: Picamera2, jsonConfig: str):
    if jsonConfig is not None:
        camera.set_controls({"AfMode": controls.AfModeEnum.Manual})
        camera.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
        with open(jsonConfig) as f:
            settings = json.load(f)
            print(settings, flush=True)
            for setting, value in settings.items():
                camera.set_controls({setting: value})

def is_backup_available(backup_path: str) -> bool:
    # Check if the path exists and is mounted
    try:
        return Path(backup_path).exists() and os.path.ismount(backup_path)
    except Exception as e:
        print(f"Error checking backup availability: {e}", flush=True)
        return False

if __name__ == "__main__":
    Path(args.data).mkdir(parents=True, exist_ok=True)
    picam = Picamera2(int(args.camera))
    config = picam.create_still_configuration()
    picam.configure(config)
    picam.start()
    time.sleep(1)
    cameraControls(picam, args.config)

    time.sleep(2)

    backup_connected = False

    while True:
        try:
            snapshot(picam, args.data, args.backup)
        except Exception as e:
            print(f"Error during snapshot capture: {e}", flush=True)

        # Check backup drive status
        if is_backup_available(args.backup):
            if not backup_connected:
                print("Backup drive reconnected. Resuming saving to USB.", flush=True)
                backup_connected = True
        else:
            if backup_connected:
                print("Backup drive disconnected. Saving to SD card only.", flush=True)
                backup_connected = False

        time.sleep(args.timer)
