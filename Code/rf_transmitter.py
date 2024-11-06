from pathlib import Path
import numpy as np
import time
import os
import re
import argparse
import serial

import glob
import os


class supervisorObject:
    sizeDelta = 0
    displayed = False


    def __init__(self, programDict:dict):
        self.name = programDict["program"]
        self.shorthand = "".join(re.findall(r'(?:^|_)(\w)', self.name))
        locationTest = re.search(r'(?<=--data\s)[^\s]+', programDict["command"])
        if locationTest is not None:
            self.location = Path(locationTest.group())
            self.folderSize = self._getFolderSize(self.location)
        else:
            self.location = None
        self.updateTime = time.monotonic_ns()
        self._objectInformation = programDict
        self.getStatus()

    def _getFolderSize(self, folder:Path):
        return sum(f.stat().st_size for f in folder.glob('**/*') if f.is_file())
    
    # Function to determine the appropriate units for folder size
    def _get_appropriate_byte(self, fsize):
        for funit in ['B', 'kB', 'MB', 'GB']:
            if len(str(fsize)) > 4:
                fsize = np.round(fsize/1024, decimals=1)
                continue
                
            fsize_str = f'{fsize} {funit}/s'
            return fsize_str

    def getStatus(self):
        #re.findall(r'[\w:]+', text)
        try:
            statusData = os.popen(f"sudo supervisorctl status {self.name}").read()
            if "RUNNING" in statusData:
                self.status = True
            elif "STARTING" in statusData:
                self.status = False
            elif "BACKOFF" in statusData:
                self.status = False
            elif "STOPPED" in statusData:
                self.status = False
            else:
                self.status = False
        except:
            self.status = False

        return self.status
    
    def getSizeDelta(self):
        oldFolderSize = self.folderSize
        oldTime = self.updateTime
        currentFolderSize = self._getFolderSize(self.location)
        currentTime = time.monotonic_ns()
        sizeDelta = ((currentFolderSize-oldFolderSize)/((currentTime-oldTime)/1000000000))
        self.sizeDelta=sizeDelta
        self.folderSize = currentFolderSize
        self.updateTime = currentTime
        return sizeDelta

    def generateProgramString(self):
        status = self.getStatus()
        if status:
            statusString = circle
        else:
            statusString = cross

        shorthandfmtd = "{: <4}".format(f"{self.shorthand}")
        
        sizeDelta = self.getSizeDelta()

        sizeString = self._get_appropriate_byte(sizeDelta)

        return "{: <21}".format(f"{statusString} | {shorthandfmtd} | {sizeString}")


def serialTransmit(port:str, gpsObject:supervisorObject, eventObject:supervisorObject):
 
    with serial.Serial(port, baudrate=57600, timeout=1) as ser:
        while(True):
            eventBytes = eventObject.getSizeDelta()
            list_of_files = glob.glob(str(gpsObject.location)+"/*") # * means all if need specific format then *.csv
            lastGPSFile = max(list_of_files, key=os.path.getctime)
            with open(lastGPSFile) as f:
                recentGPSData = "".join(f.readlines()[-50:-1])
            recentCoords = re.findall(r'^\$GNRMC.*', recentGPSData, re.M)[-1]
            output = f"{eventBytes}\r\n{recentCoords}\r\n".encode("utf-8")
            print(output)
            ser.write(output)
            time.sleep(2)
   
if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("port", help="Serial Port for GPS", type=str)
    args = parser.parse_args()
    port = serial.Serial(args.port, baudrate=57600, timeout=1)


    print("Daedalus RF Transmitter\n")
    
    time.sleep(1)
    

    with open("../config/supervisord.conf", "r") as config:
        configString = "".join(config.readlines())

    programs = re.findall(r'\[program:[\s\S]*?\r?\n\r?\n', configString)
    supervisorDict = {}
    for program in programs:
        programDict = {}
        programLines = program.split("\n")
        for num, line in enumerate(programLines):
            if num == 0:
                programDict["program"] = re.search(r'(?<=\[program:)[^\]]+(?=\])', programLines[0]).group()
            elif line != "":
                splitLines = line.split("=")
                programDict[splitLines[0]]=splitLines[1]

        supervisorDict[programDict["program"]] = supervisorObject(programDict)

    
    serialTransmit(args.port, supervisorDict["g_p_s"], supervisorDict["event_based_camera"])       
