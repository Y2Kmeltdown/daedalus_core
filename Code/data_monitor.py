import qwiic_oled_display
from pathlib import Path
import sys
import numpy as np
import time
import os
import re

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

        return "{: <21}".format(f"{statusString} |{shorthandfmtd} |{sizeString}")

def run_display(display_string, myOLED):

    if myOLED.is_connected() == False:
        print("The Qwiic OLED Display isn't connected to the system. Please check your connection", \
            file=sys.stderr)
        return
    
    myOLED.begin()
    # ~ myOLED.clear(myOLED.ALL)
    myOLED.clear(myOLED.PAGE)  #  Clear the display's buffer
    myOLED.print(display_string)
    print(display_string, flush=True)
    myOLED.display()

if __name__ == '__main__':
    # Initialise display
    #tick = "✓"
    #cross = "✗"

    circle = "O"
    cross = "X"
    pageSize = 4
    print("Daedalus OLED Display\n")
    myOLED = qwiic_oled_display.QwiicOledDisplay()
    time.sleep(1)
    myOLED.begin()
    run_display("Daedalus OLED Display initialising...", myOLED)

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

    numberOfPages = len(supervisorDict)//pageSize
    # Parse supervisor.conf to get info about running components and attribute a data location to each program if they have a data location
    # Generate Supervisor Objects with all the info in them as a list of objects
    # Generate appropriate number of pages on the OLED for the programs that generate data

    #TODO Update this to always show event camera on 1st row
    while True:
        for page in range(numberOfPages): # Loop through 4 times to generate data for each row in the page
            pageUsage = 0
            programStrings = []
            for supervisorObject in supervisorDict.values():
                if pageUsage < pageSize:
                    if supervisorObject.location is not None and supervisorObject.displayed == False:
                        programStrings.append(supervisorObject.generateProgramString())
                        pageUsage+=1
                        supervisorObject.displayed = True
                else:
                    break
            if programStrings:   
                oled_string = "".join(programStrings)
                run_display(oled_string, myOLED)
                time.sleep(3)
        for supervisorObject in supervisorDict.values():
            supervisorObject.displayed = False        
