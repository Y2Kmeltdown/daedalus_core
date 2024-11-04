import time
import argparse
import json
import os
from pathlib import Path

from picamera2 import Picamera2
from libcamera import controls
from picamera2.encoders import H264Encoder, Quality

dirname = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("camera", help="Camera number (for example 0 or 1)")
parser.add_argument(
    "--data",
    default=str(dirname / "vid_recordings"),
    help="Path of the directory where recordings are stored",
)
parser.add_argument(
    "--backup",
    default=str("/mnt/data"),
    help="Path of the directory where recordings are backed up",
)
    "--vid_duration",
    default=60,
    type=int,
parser.add_argument(
    "--config",
    type=str,
    help="Path to configuration json for camera properties",
)
args = parser.parse_args()

def cameraControls(camera: Picamera2, jsonConfig: str):
    if jsonConfig is not None:
        camera.set_controls({"AfMode": controls.AfModeEnum.Manual})
        camera.set_controls({"NoiseReductionMode": controls.draft.NoiseReductionModeEnum.Off})
        with open(jsonConfig) as f:
            settings = json.load(f)
            print(settings, flush=True)
            for setting, value in settings.items():
                camera.set_controls({setting: value})

def is_usb_connected(mount_point: str) -> bool:
    """
    Check if the USB mount point is accessible.
    """
    return Path(mount_point).is_dir() and os.access(mount_point, os.W_OK)

def start_video_recording(camera: Picamera2, data_path: str, backup_path: str, duration: int):
    """
    Start video recording, saving to both primary and backup directories.
    If the backup (USB) fails, continue recording to the primary (SD card).
    """
    timestr = time.strftime("%Y%m%d-%H%M%S")
    sd_filename = Path(data_path) / f'cam_{camera.camera_idx}_vid_{timestr}.h264'
    usb_filename = Path(backup_path) / f'cam_{camera.camera_idx}_vid_{timestr}.h264'

    # Create output directories if they don't exist
    Path(data_path).mkdir(parents=True, exist_ok=True)
    Path(backup_path).mkdir(parents=True, exist_ok=True)

    encoder_sd = H264Encoder()
    encoder_usb = H264Encoder()

    # Start recording to SD card
    camera.start_recording(encoder_sd, str(sd_filename))
    print(f"Recording started on SD card: {sd_filename}", flush=True)

    # Attempt to start recording to USB drive
    usb_recording = False
    if is_usb_connected(backup_path):
        try:
            camera.start_recording(encoder_usb, str(usb_filename))
            usb_recording = True
            print(f"Recording started on USB drive: {usb_filename}", flush=True)
        except Exception as e:
            print(f"Error starting recording on USB drive: {e}", flush=True)
    else:
        print("USB drive not connected. Recording only to SD card.", flush=True)

    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            time.sleep(0.1)
            # Check if USB is disconnected during recording
            if usb_recording and not is_usb_connected(backup_path):
                try:
                    camera.stop_recording(encoder_usb)
                    usb_recording = False
                    print(f"USB disconnected. Stopped recording on USB drive: {usb_filename}", flush=True)
                except Exception as e:
                    print(f"Error stopping recording on USB drive: {e}", flush=True)
                    usb_recording = False
    finally:
        # Stop recording on SD card
        try:
            camera.stop_recording(encoder_sd)
            print(f"Recording stopped on SD card: {sd_filename}", flush=True)
        except Exception as e:
            print(f"Error stopping recording on SD card: {e}", flush=True)

        # Stop recording on USB if still recording
        if usb_recording:
            try:
                camera.stop_recording(encoder_usb)
                print(f"Recording stopped on USB drive: {usb_filename}", flush=True)
            except Exception as e:
                print(f"Error stopping recording on USB drive: {e}", flush=True)

if __name__ == "__main__":
    picam = Picamera2(int(args.camera))
    picam.configure("video")
    picam.start()
    time.sleep(1)
    cameraControls(picam, args.config)

    while True:
        start_video_recording(picam, args.data, args.backup, args.vid_duration)
