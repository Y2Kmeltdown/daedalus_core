from pathlib import Path
import sys
import numpy as np
import time
import os
import re
import argparse
import serial
from data_monitor import supervisorObject

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("port", help="Serial Port for GPS", type=str)
    parser.add_argument(
        "--data",
        default="/usr/local/daedalus/data",
        help="Path of the directory where recordings are stored",
    )
    args = parser.parse_args()
    

    with open("../config/supervisord.conf", "r") as config:
        configString = "".join(config.readlines())

    program = re.findall(r'\[program:event_camera][\s\S]*?\r?\n\r?\n', configString)[0]
    
    
    programDict = {}
    programLines = program.split("\n")
    for num, line in enumerate(programLines):
        if num == 0:
            programDict["program"] = re.search(r'(?<=\[program:)[^\]]+(?=\])', programLines[0]).group()
        elif line != "":
            splitLines = line.split("= ")
            programDict[splitLines[0]]=splitLines[1]

    event_supervisor = supervisorObject(programDict)

    with serial.Serial(args.port, baudrate=57600, timeout=1) as ser:
        while(True):
            eventBytes = event_supervisor.getSizeDelta()
            ser.write(eventBytes)
            time.sleep(2)

    