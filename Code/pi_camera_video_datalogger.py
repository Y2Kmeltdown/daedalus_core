import time
import argparse
import json

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
    "--vid_duration",
    default=60,
    type=int,
    help="Time for each video duration in seconds",
)
parser.add_argument(
    "--config",
    type=str,
    help="Path to configuration json for camera properties",
)
args = parser.parse_args()

# def record_timestamp(request):
#     timestamp = time.strftime("%Y%m%d-%H%M%S")
#     print(timestamp)

def cameraControls(camera:Picamera2, jsonConfig:str):
    if jsonConfig is not None:
        camera.set_controls({"AfMode" : controls.AfModeEnum.Manual}) # Autofocus mode set last word to either Manual, Auto or Continuous
        camera.set_controls({"NoiseReductionMode" : controls.draft.NoiseReductionModeEnum.Off}) # Noise Reduction Mode set last word to either Off, Fast or HighQuality
        with open(jsonConfig) as f:
            
            settings = json.load(f)
            print(settings, flush=True)
            for setting, value in settings.items():
                camera.set_controls({setting:value})
            #testItem = "AnalogueGain"
            #min_val, max_val, default_val = picam2.camera_controls[testItem]
            #print((min_val, max_val, default_val))
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
    

if __name__ == "__main__":
    Path(args.data).mkdir(parents=True, exist_ok=True)

    picam = Picamera2(int(args.camera))
    # config = picam.create_video_configuration(controls={"FrameDurationLimits": (40000, 100000)})
    picam.configure("video")
    # picam.pre_callback = record_timestamp
    picam.start()
    time.sleep(1)
    cameraControls(picam, args.config)

    encoder = H264Encoder()

    while True:
        timestr = time.strftime("%Y%m%d-%H%M%S")
        output = f'{args.data}/cam_{picam.camera_idx}_vid_{timestr}'

        picam.start_encoder(encoder, f'{output}.h264',quality=Quality.HIGH)
        time.sleep(args.vid_duration)
        picam.stop_encoder()

    picam.stop()