import qwiic_oled_display
from pathlib import Path
import sys
import numpy as np
import time
import os
import re
import daedalus_utils

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
    supervisorFile = "../config/supervisord.conf"
    pageSize = 4
    print("Daedalus OLED Display\n")
    myOLED = qwiic_oled_display.QwiicOledDisplay()
    time.sleep(1)
    myOLED.begin()
    run_display("Daedalus OLED Display initialising...", myOLED)

    daedalus = daedalus_utils.supervisor(supervisorFile)

    numberOfPages = len(daedalus.moduleDict)//pageSize
    
    #TODO Update this to always show event camera on 1st row
    while True:
        for page in range(numberOfPages): # Loop through 4 times to generate data for each row in the page
            pageUsage = 0
            programStrings = []
            for supervisorObject in daedalus.moduleDict.values():
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
        for supervisorObject in daedalus.moduleDict.values():
            supervisorObject.displayed = False        
