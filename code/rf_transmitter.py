import time
import serial
import threading
import queue

from pathlib import Path
import numpy as np
import os
import re
import argparse

import glob
import os

import daedalus_utils

def generateDataString(gpsObject:daedalus_utils.supervisor.supervisorModule, eventObject:daedalus_utils.supervisor.supervisorModule):
    eventBytes = eventObject.getSizeDelta()
    list_of_files = glob.glob(str(gpsObject.location)+"/*") # * means all if need specific format then *.csv
    if list_of_files:
        print(type(list_of_files))
        lastGPSFile = max(list_of_files, key=os.path.getctime)
        with open(lastGPSFile) as f:
            recentGPSData = "".join(f.readlines()[-50:-1])
            recentCoords = re.findall(r'^\$GNRMC.*', recentGPSData, re.M)[-1]
    else:
        recentCoords = "No GPS Data Found"

    output = f"{eventBytes}\r\n{recentCoords}\r\n".encode("utf-8")
    print(output)

    return output
        
if __name__ == '__main__':

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
        help="Serial Port for GPS", 
        type=str)
    args = parser.parse_args()

    #port = "COM8"
    baudrate = "57600"
    supervisorFile = "../config/supervisord.conf"
    

    rf_transceiver = daedalus_utils.transceiver(args.port, baudrate)
    daedalus = daedalus_utils.supervisor(supervisorFile)

    print("Daedalus RF Transmitter\n")
    
    time.sleep(1)

    while True:
        dataString = generateDataString(daedalus.moduleDict["g_p_s"], daedalus.moduleDict["event_based_camera"])
        rf_transceiver.transmit(dataString)
        time.sleep(2)
