#!/usr/bin/env python
#-----------------------------------------------------------------------------
# imu_reader.py
#
# Script to read data over I2C from two ICM20948 boards using the Adafruit ICM libraries
#
#==================================================================================

import time
from datetime import datetime
import sys
import csv
import os
import argparse
from pathlib import Path
import board
import adafruit_icm20x

ADDRESS_1 = 0x69
ADDRESS_2 = 0x68

def readIMU(i2c_address, dir_path):
	
	i2c = board.I2C()  # uses board.SCL and board.SDA

	icm = adafruit_icm20x.ICM20948(i2c,i2c_address)

	print("\nDaedalus IMU Reader\n")

	fieldnames = ['Timestamp', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz']

	if not os.path.isdir(dir_path):
		os.makedirs(dir_path)

	print(dir_path)

	start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
	filename = "imu-data_" + start_time + ".csv"
	
	with open(os.path.join(dir_path, filename), 'w', newline='') as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()
			
		while True:
			print("Writing data...")
			
			# Update and write data from first IMU
			accel = icm.acceleration
			gyro = icm.gyro
			mag = icm.magnetic
			
			IMU_data = {'Timestamp': datetime.now(),
			'ax': accel[0], 
			'ay': accel[1], 
			'az': accel[2],
			'gx': gyro[0],
			'gy': gyro[1],
			'gz': gyro[2],
			'mx': mag[0],
			'my': mag[1],
			'mz': mag[2]}
			
			writer.writerow(IMU_data) 
		
			time.sleep(0.01)


if __name__ == '__main__':

	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	parser.add_argument("i2c_address", help="I2C address for IMU")
	parser.add_argument(
		"--path",
		default=str(Path.home() / 'data/imu_horizon'),
		help="Path to folder to save IMU data",
	)
	args = parser.parse_args()

	try:
		readIMU(args.i2c_address, args.path)
	except (KeyboardInterrupt, SystemExit) as exErr:
		print("\nEnding imu_reader.py")
		sys.exit(0)
