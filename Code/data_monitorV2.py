import os
import qwiic_oled_display
from pathlib import Path
import sys
import argparse
import numpy as np
from time import sleep
import logging
import subprocess

###############TODO REWRITE WITH SUPERVISOR CTL COMMANDS AND TICK OR CROSSES FOR EACH COMPONENT #############################
tick = "✓"
cross = "✗"

class supervisorObject:
    size_delta = 0


    def __init__(self, name, data_location):
        self.name = name
        self.location = data_location
        #self.shorthand = getFirstLetterOfEachWord(self.name)
        #self.folder_size = get_folder_size(self.location)
        #self.update_time = time.monotonic_ns()

    def getStatus(self):
        #subprocess run supervisor ctl
        #filter by name
        #If running
        #self.status = True
        #Else
        #self.status = False
        #return self.status
        pass

    def generateProgramString(self):
        # Get status
        # Get current File size
        # Get current program time
        # Get data path delta size
        # Set status string to tick or cross
        # 
        # Write String f"{statusString}:{programShorthand} {data delta}"

        pass


# Function to display a string on the OLED
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

# Function to get the folder size of a single folder
def get_folder_size(folder_path):
    total_size = 0.0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
    return np.max([0.1,total_size]) # Prevent zero error by setting minimum file size

# Function to get the diff in file size
def get_size_deltas(initial_sizes, final_sizes):
    size_deltas = []
    perc_deltas = []
    for initial_size, final_size in zip(initial_sizes, final_sizes):
        size_delta = np.round((final_size - initial_size), decimals=1)
        perc_delta = np.round(size_delta/initial_size*100, decimals=1)
        
        size_delta_str = get_appropriate_byte(size_delta)
        
        size_deltas.append(size_delta_str)
        perc_deltas.append(perc_delta)

    return size_deltas, perc_deltas

# Function to determine the appropriate units for folder size
def get_appropriate_byte(fsize):
    for funit in ['B', 'kB', 'MB', 'GB']:
        if len(str(fsize)) > 4:
            fsize = np.round(fsize/1024, decimals=1)
            continue
            
        fsize_str = f'{fsize}{funit}'
        return fsize_str
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
		"--data",
		default=str(Path.home() / 'data'),
		help="Path of parent folder. Assumed to have folders ['evk4_horizon', 'cmos_horizon', 'imu_horizon', 'evk4_space',  'cmos_space', 'imu_space'] unless a specific path is given as an argument.",
	)
    args = parser.parse_args()

    # Initialise display
    print("Daedalus OLED Display\n")
    myOLED = qwiic_oled_display.QwiicOledDisplay()
    sleep(1)
    myOLED.begin()
    run_display("Daedalus OLED Displayinitialising...", myOLED)

    #Parse supervisor.conf to get info about running components and attribute a data location to each program if they have a data location
    #Generate Supervisor Objects with all the info in them as a list of objects
    #Generate appropriate number of pages on the OLED for the programs that generate data

    #While true
    #   For page in len(numberOfPages)
    #       pageUsage = 0
    #       programStrings = []
    #       For supervisorObject in supervisorObjects
    #           if pageUsage < pageCapacity
    #               if supervisorObject.hasData == True and supervisorObject.displayed == False
    #                   programStrings.append(supervisorObject.generateProgramString())
    #                   pageUsage+=1
    #                   supervisorObject.displayed = True
    #           else break
    #       oled_string = "\n".join(programStrings)
    #       run_display(oled_string, myOLED)
    #       sleep(3)
    #           