#!/usr/bin/env python
#-----------------------------------------------------------------------------
# imu_reader.py
#
# Script to read data over I2C from two ICM20948 boards using the Adafruit ICM libraries
#
#==================================================================================

import time
from datetime import datetime
import os
import argparse
from pathlib import Path
import board
from bmi270.BMI270 import *


#ADDRESS_1 = 0x69
#ADDRESS_2 = 0x68
def imuInit(i2c_address):
    try:
        BMI270_1 = BMI270(i2c_address)
        BMI270_1.load_config_file()
    except Exception as e:
        print("Error: " + str(e))
        print("Could not initialize BMI270_1. Check your wiring or try again.")
        exit(1)
		
    BMI270_1.set_mode(PERFORMANCE_MODE)
    BMI270_1.set_acc_range(ACC_RANGE_2G)
    BMI270_1.set_gyr_range(GYR_RANGE_1000)
    BMI270_1.set_acc_odr(ACC_ODR_200)
    BMI270_1.set_gyr_odr(GYR_ODR_200)
    BMI270_1.set_acc_bwp(ACC_BWP_OSR4)
    BMI270_1.set_gyr_bwp(GYR_BWP_OSR4)
    BMI270_1.disable_fifo_header()
    BMI270_1.enable_data_streaming()
    BMI270_1.enable_acc_filter_perf()
    BMI270_1.enable_gyr_noise_perf()
    BMI270_1.enable_gyr_filter_perf()
	
    return BMI270_1

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--i2c_address", help="I2C address for IMU in hexadecimal", type=lambda x: int(x, 16))
parser.add_argument(
    "--data",
    default="/usr/local/daedalus/data/imu",
    help="Path of the directory where recordings are stored",
)
parser.add_argument(
    "--backup",
    default="/mnt/data/imu",
    help="Path of the directory where recordings are backed up",
)
args = parser.parse_args()

def ensure_directory_exists(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)

def generate_file_name(base_dir):
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"imu_data_{current_time}.txt"
    return os.path.join(base_dir, file_name)

def save_imu_data(file_path, data):
    try:
        with open(file_path, 'a') as file:
            file.write(data)
            file.flush()
    except Exception as e:
        return False
    return True

def read_imu(i2c_address, data_path, backup_path):
    bmi = imuInit(i2c_address)
    print("Starting IMU Reader...")

    ensure_directory_exists(data_path)
    ensure_directory_exists(backup_path)

    data_file_sd = generate_file_name(data_path)
    data_file_usb = generate_file_name(backup_path)
    usb_connected = True

    try:
        while True:
            accel = bmi.get_acc_data()
            gyro = bmi.get_gyr_data()
    
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_line = f"{timestamp}\tax:{accel}\tgy:{gyro}\n"
            
            # Always save to SD
            print(f"Saving IMU to SD: {data_file_sd}")
            save_imu_data(data_file_sd, data_line)

            # Conditionally save to USB
            if usb_connected:
                print(f"Saving IMU to USB: {data_file_usb}")
                usb_connected = save_imu_data(data_file_usb, data_line)
                if not usb_connected:
                    print("USB drive became unavailable. Saving to SD only.")

            # Every 60 seconds, generate new filenames
            if (datetime.now() - datetime.strptime(data_file_sd[-19:-4], "%Y%m%d_%H%M%S")).seconds >= 60:
                data_file_sd = generate_file_name(data_path)
                if usb_connected:
                    data_file_usb = generate_file_name(backup_path)
                    # print(f"New files created: {data_file_sd} and {data_file_usb}\n")
                    # print(f"New files created: {data_file_sd} and {data_file_usb}\n")
                # else:
                #     print(f"New file created on SD: {data_file_sd}")

            time.sleep(1)  # Sleep for 1 second between readings

    except (KeyboardInterrupt, SystemExit):
        print("Stopping IMU Reader.")

if __name__ == '__main__':
    read_imu(args.i2c_address, args.data, args.backup)
