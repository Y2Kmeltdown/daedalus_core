import time
import datetime
import json
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


def snapshot(camera:Picamera2):

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

    if camera.camera_idx == 0:
        foldername = 'cmos_space'
    elif camera.camera_idx == 1:
        foldername = 'cmos_horizon'

    with open(Path.home() / f'data/{foldername}/cam_{camera.camera_idx}_metadata_{timestr}.json', 'w') as f:
        f.write(json.dumps([imgMetadata2, imgMetadata]))
    request.save('main', Path.home() / f'data/{foldername}/cam_{camera.camera_idx}_image_{timestr}.png')
    request.release()


def cameraControls(camera:Picamera2):
    #testItem = "AnalogueGain"
    #min_val, max_val, default_val = picam2.camera_controls[testItem]
    #print((min_val, max_val, default_val))
    camera.set_controls({"AfMode" : controls.AfModeEnum.Manual}) # Autofocus mode set last word to either Manual, Auto or Continuous
    camera.set_controls({"NoiseReductionMode" : controls.draft.NoiseReductionModeEnum.Off}) # Noise Reduction Mode set last word to either Off, Fast or HighQuality
    camera.set_controls({"AeEnable" : False}) # Auto Exposure enable True or False
    camera.set_controls({"LensPosition" : 32}) # Lens Postion values 0 to 32 metadata reports 15 as max??? Values in meters
    camera.set_controls({"ExposureTime" : 10000}) # Exposure time values 0 to 220417486 metadata reports inconsistant values ranging from 12000 to 16000 when set to max value??? Values are in microseconds
    #picam2.set_controls({"AnalogueGain" : 0}) # Analogue Gain values 1 to 16
    #picam2.set_controls({"DigitalGain" : 0}) # According to docs don't bother messing with digital gain
    #picam2.set_controls({"ExposureValue" : 0})
    #picam2.set_controls({"Brightness" : 0})
    #picam2.set_controls({"Contrast" : 16})
    #picam2.set_controls({"Saturation" : 11})
    #picam2.set_controls({"Sharpness" : 8})
    pass

if __name__ == "__main__":

    
    picam0 = Picamera2(0)
    config = picam0.create_still_configuration()
    picam0.configure(config)
    

    try:
        picam1 = Picamera2(1)
        config = picam1.create_still_configuration()
        picam1.configure(config)
    except:
        pass

    picam0.start()
    
    try:
        picam1.start()
    except:
        pass

    time.sleep(1)

    cameraControls(picam0)

    try:
        cameraControls(picam1)
    except:
        pass
    

    time.sleep(2)
    # snapshot(picam0)
    # try:
    #     snapshot(picam1)
    # except:
    #     pass
    
    

    # TODO UNCOMMENT THIS WHEN FINISHED TESTING
    while True:
        snapshot(picam0)
        
        try:
            snapshot(picam1)
        except:
            pass
    
        
        time.sleep(10)
