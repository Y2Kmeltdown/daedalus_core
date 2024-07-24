import time
import datetime
import json
import argparse
from pathlib import Path
from picamera2 import Picamera2
from libcamera import controls

def check_request_timestamp(request, check_time):
    md = request.get_metadata()
    # 'SensorTimestamp' is when the first pixel was read out, so it started being
    # exposed 'ExposureTime' earlier.
    exposure_start_time = md['SensorTimestamp'] - 1000 * md['ExposureTime']
    if exposure_start_time < check_time:
        print("ERROR: request captured too early by", check_time - exposure_start_time, "nanoseconds")

def snapshot(camera:Picamera2, data_path:str):

    timestr = time.strftime("%Y%m%d-%H%M%S")
    ct = datetime.datetime.now()
    check_time = time.monotonic_ns() + 5e8
    job = camera.capture_request(flush=check_time, wait=False)

    request = camera.wait(job)
    check_request_timestamp(request, check_time)
    imgMetadata = request.get_metadata()
    imgMetadata2 = {
        "filename":f"cam_{camera.camera_idx}_image_{timestr}.png",
        "timestamp":str(ct),
        "timestamp(ns)":check_time
    }
    
    with open(f'{data_path}/cam_{camera.camera_idx}_metadata_{timestr}.json', 'w') as f:
        f.write(json.dumps([imgMetadata2, imgMetadata]))
    request.save('main', f'{data_path}/cam_{camera.camera_idx}_image_{timestr}.png')
    request.release()

def cameraControls(camera:Picamera2, jsonConfig:str):
    if jsonConfig is not None:
        settings = json.load(jsonConfig)
        for setting, value in settings:
            camera.set_controls({setting:value})
        #testItem = "AnalogueGain"
        #min_val, max_val, default_val = picam2.camera_controls[testItem]
        #print((min_val, max_val, default_val))
        #camera.set_controls({"AfMode" : controls.AfModeEnum.Manual}) # Autofocus mode set last word to either Manual, Auto or Continuous
        #camera.set_controls({"NoiseReductionMode" : controls.draft.NoiseReductionModeEnum.Off}) # Noise Reduction Mode set last word to either Off, Fast or HighQuality
        #camera.set_controls({"AeEnable" : False}) # Auto Exposure enable True or False
        #camera.set_controls({"LensPosition" : 32}) # Lens Postion values 0 to 32 metadata reports 15 as max??? Values in meters
        #camera.set_controls({"ExposureTime" : 10000}) # Exposure time values 0 to 220417486 metadata reports inconsistant values ranging from 12000 to 16000 when set to max value??? Values are in microseconds
        #picam2.set_controls({"AnalogueGain" : 0}) # Analogue Gain values 1 to 16
        #picam2.set_controls({"DigitalGain" : 0}) # According to docs don't bother messing with digital gain
        #picam2.set_controls({"ExposureValue" : 0})
        #picam2.set_controls({"Brightness" : 0})
        #picam2.set_controls({"Contrast" : 16})
        #picam2.set_controls({"Saturation" : 11})
        #picam2.set_controls({"Sharpness" : 8})

dirname = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("camera", help="Camera number (for example 0 or 1)")
parser.add_argument(
    "--data_path",
    default=str(dirname / "recordings"),
    help="Path of the directory where recordings are stored",
)
parser.add_argument(
    "--config",
    type=str,
    help="Path to configuration json for camera properties",
)
args = parser.parse_args()

if __name__ == "__main__":
    
    
    
    picam = Picamera2(int(args.camera))
    config = picam.create_still_configuration()
    picam.configure(config)
    picam.start()
    time.sleep(1)
    cameraControls(picam, args.config)

    time.sleep(2)
    # snapshot(picam0, args.data_path)

    # TODO UNCOMMENT THIS WHEN FINISHED TESTING
    while True:
        snapshot(picam, args.data_path)
        time.sleep(10)
