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

switch_num = 2
delay = 5 # seconds
folder_main = Path.home() / 'data'
folder_names = ['evk4_horizon', 'cmos_horizon', 'imu_horizon', 'evk4_space',  'cmos_space', 'imu_space']
folder_path_alias = ['Eh', 'Ch', 'Ih', 'Es', 'Cs', 'Is']



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

# Function to get paths of folders to check size of
def get_folder_paths(args_dict):
    folder_paths = []
    for folder in folder_names:
        main_dir = args_dict['data']
        folder_path = os.path.join(main_dir, folder)
        folder_paths.append(folder_path)

    # Check no path has been overwritten
    for i, alias in enumerate(folder_path_alias):
        if args_dict[alias] is not None:
            folder_paths[i] = args_dict[alias]
    
    return folder_paths

# Function to get the array of folder sizes 
def get_fsizes(folder_paths, main_dir):
    fsizes = []
    for folder in folder_paths:
        fsize = get_folder_size(f'{folder}')
        fsizes.append(fsize)
    return fsizes

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

# Function that gets change in folder size and formats strings for OLED display
def make_folder_strings(initial_sizes, final_sizes):
    size_deltas, perc_deltas = get_size_deltas(initial_sizes, final_sizes)
    
    # Add space buffers to create new lines (21 characters for each line of OLED)
    display_string_horizon = '{: <21}'.format('Horizon data')
    display_string_space = '{: <21}'.format('Space data')
    for i, folder, size, perc in zip(range(len(folder_path_alias)), folder_path_alias, size_deltas, perc_deltas):
        folder_string = f'{folder} {size}|{perc}%'
        folder_string = '{: <21}'.format(folder_string)
        
        if i < 3:
            display_string_horizon += folder_string
        else:
            display_string_space += folder_string
    
    return display_string_horizon, display_string_space




if __name__ == '__main__':

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
		"--data",
		default=str(Path.home() / 'data'),
		help="Path of parent folder. Assumed to have folders ['evk4_horizon', 'cmos_horizon', 'imu_horizon', 'evk4_space',  'cmos_space', 'imu_space'] unless a specific path is given as an argument.",
	)
    parser.add_argument(
		"--Eh",
		help="Full path to folder containing the horizon event camera data.",
	)
    parser.add_argument(
		"--Ch",
		help="Full path to folder containing the horizon cmos data.",
	)
    parser.add_argument(
		"--Ih",
		help="Full path to folder containing the horizon IMU data.",
	)
    parser.add_argument(
		"--Es",
		help="Full path to folder containing the space event camera data.",
	)
    parser.add_argument(
		"--Cs",
		help="Full path to folder containing the space cmos data.",
	)
    parser.add_argument(
		"--Is",
		help="Full path to folder containing the space IMU data.",
	)

    args = parser.parse_args()
    folder_paths = get_folder_paths(vars(args))
    print(folder_paths)
    
    # Initialise display
    print("Daedalus OLED Display\n")
    myOLED = qwiic_oled_display.QwiicOledDisplay()
    sleep(1)
    myOLED.begin()
    run_display("Daedalus OLED Displayinitialising...", myOLED)
    
    initial_sizes = get_fsizes(folder_paths, args.data)
    sleep(delay)
    final_sizes = get_fsizes(folder_paths, args.data)
    
    # Main loop
    while True:
        curr_display_string = ''
        try:
            # Get folder deltas and make string for display
            display_string_h, display_string_s = make_folder_strings(initial_sizes, final_sizes)
            
            # Switch display between horizon and space folder sizes 
            for i in range(switch_num):
                if curr_display_string == display_string_h:
                    curr_display_string = display_string_s
                else:
                    curr_display_string = display_string_h
                    
                run_display(curr_display_string, myOLED)
                sleep(delay/switch_num)
            
            # Update folder sizes    
            initial_sizes = final_sizes
            final_sizes = get_fsizes(folder_paths, args.data)

             
        except (KeyboardInterrupt, SystemExit) as exErr:
            print("\Exiting fsize delta script.")
            sys.exit(0)

    

