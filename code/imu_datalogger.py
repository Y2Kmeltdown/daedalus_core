#!/usr/bin/env python
#-----------------------------------------------------------------------------
# imu_reader.py
#
# Script to read data over I2C from two ICM20948 boards using the Adafruit ICM libraries
#
#==================================================================================

import time
from datetime import datetime, timedelta
import os
import argparse
from pathlib import Path
import board
from bmi270.BMI270 import *
import adafruit_icm20x
import daedalus_utils


#ADDRESS_1 = 0x69
#ADDRESS_2 = 0x68
def bmi270Init(i2c_address):
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

def read_imu(i2c_address, imuDataHandler, record_time):

    try:
        i2c = board.I2C()  # uses board.SCL and board.SDA
        icm = adafruit_icm20x.ICM20948(i2c, i2c_address)
        icm20x = True
    except:
        icm20x = False

    try:
        bmi = bmi270Init(i2c_address)
        bmi270 = True
    except:
        bmi270 = False
    
    print("Starting IMU Reader...")
    
    buffer = []
    last_save_time = datetime.now()
    buffer_save_interval = timedelta(seconds=10)  # Save buffer every 10 seconds
    last_buffer_save = datetime.now()

    try:
        while True:

            if icm20x:
                accel = icm.acceleration
                gyro = icm.gyro
                mag = icm.magnetic
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_line = f"{timestamp}\tax:{accel}\tgy:{gyro}\tmag:{mag}\n"
                buffer.append(data_line)
            elif bmi270:
                accel = bmi.get_acc_data()
                gyro = bmi.get_gyr_data()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data_line = f"{timestamp}\tax:{accel}\tgy:{gyro}\n"
                buffer.append(data_line)
            
            
            # Save buffer to files every 10 seconds
            if datetime.now() - last_buffer_save >= buffer_save_interval and buffer:
                print(f"[INFO] Writing buffer at {datetime.now().strftime('%H:%M:%S')}...")
                
                imuDataHandler.write_data(buffer)

                buffer.clear()  # Clear buffer after writing
                last_buffer_save = datetime.now()

            # Every 60 seconds, generate new filenames
            if (datetime.now() - last_save_time).total_seconds() >= record_time:
                print(f"\n[INFO] Creating new file at {datetime.now().strftime('%H:%M:%S')}")
                last_save_time = datetime.now()
                imuDataHandler.generate_filename()
                imuDataHandler.validate_savepoints()

            time.sleep(1)  # Sleep for 1 second between readings

    except (KeyboardInterrupt, SystemExit):
        print("Stopping IMU Reader.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--i2c_address",
        default="0x68", 
        help="I2C address for IMU in hexadecimal", 
        type=lambda x: int(x, 16))
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
    parser.add_argument(
        "--socket",
        default=str("/tmp/imu.sock"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--record_time",
        default=300,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()
    imuDataHandler = daedalus_utils.data_handler(
        sensorName="imu", 
        extension = ".txt", 
        dataPath=args.data, 
        backupPath=args.backup,
        socketPath=args.socket
        )
    read_imu(args.i2c_address, imuDataHandler, args.record_time)

    
