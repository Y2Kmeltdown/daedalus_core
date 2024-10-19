import time
import datetime
import json
import argparse
from pathlib import Path

from picamera2 import Picamera2
from libcamera import controls

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
    try:
        # Save to data directory
        with open(f'{data_path}/{filename}.json', 'w') as f:
            f.write(json.dumps(imgMetadata))
        print(f'Metadata saved to {data_path}/{filename}.json', flush=True)
        request.save('main', f'{data_path}/{filename}.png')
        print(f'Snapshot saved to {data_path}/{filename}.png', flush=True)
    except Exception as e:
        print(f"Error saving to data directory: {e}. Attempting backup...", flush=True)
    
    try:
        Path(backup_path).mkdir(parents=True, exist_ok=True)
        with open(f'{backup_path}/{filename}.json', 'w') as f:
            f.write(json.dumps(imgMetadata))
        print(f'Metadata saved to {backup_path}/{filename}.json', flush=True)
        request.save('main', f'{backup_path}/{filename}.png')
        print(f'Snapshot saved to {backup_path}/{filename}.png', flush=True)
    except Exception as e:
        print(f"Error saving to backup directory: {e}. Skipping this snapshot...", flush=True)

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

if __name__ == "__main__":
    Path(args.data).mkdir(parents=True, exist_ok=True)
    picam = Picamera2(int(args.camera))
    config = picam.create_still_configuration()
    picam.configure(config)
    picam.start()
    time.sleep(1)
    cameraControls(picam, args.config)

    time.sleep(2)

    while True:
        snapshot(picam, args.data, args.backup)
        time.sleep(args.timer)
