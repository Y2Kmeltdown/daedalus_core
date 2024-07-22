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
from pathlib import Path
import board
import adafruit_icm20x

ADDRESS_1 = 0x69
ADDRESS_2 = 0x68

def read2IMU():
	
	i2c = board.I2C()  # uses board.SCL and board.SDA

	icm1 = adafruit_icm20x.ICM20948(i2c,ADDRESS_1)
	icm2 = adafruit_icm20x.ICM20948(i2c,ADDRESS_2)

	print("\nDaedalus IMU Reader\n")

	fieldnames = ['Timestamp', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz']

	dir_path = Path.home() / 'data'
	if not os.path.isdir(dir_path):
		os.makedirs(dir_path)

	start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
	filename1 = "imu_horizon/imu-h-data_" + start_time + ".csv"
	filename2 = "imu_space/imu-s-data_" + start_time + ".csv"
	
	with open(os.path.join(dir_path, filename1), 'w', newline='') as csvfile1:
		writer1 = csv.DictWriter(csvfile1, fieldnames=fieldnames)
		writer1.writeheader()

		with open(os.path.join(dir_path, filename2), 'w', newline='') as csvfile2:
			writer2 = csv.DictWriter(csvfile2, fieldnames=fieldnames)
			writer2.writeheader()
			
			while True:
				print("Writing data...")
				
				# Update and write data from first IMU
				accel = icm1.acceleration
				gyro = icm1.gyro
				mag = icm1.magnetic
				
				IMU1_data = {'Timestamp': datetime.now(),
				'ax': accel[0], 
				'ay': accel[1], 
				'az': accel[2],
				'gx': gyro[0],
				'gy': gyro[1],
				'gz': gyro[2],
				'mx': mag[0],
				'my': mag[1],
				'mz': mag[2]}
				
				writer1.writerow(IMU1_data) 
				
				# Update and write data from second IMU
				accel = icm2.acceleration
				gyro = icm2.gyro
				mag = icm2.magnetic
				
				IMU2_data = {'Timestamp': datetime.now(),
				'ax': accel[0], 
				'ay': accel[1], 
				'az': accel[2],
				'gx': gyro[0],
				'gy': gyro[1],
				'gz': gyro[2],
				'mx': mag[0],
				'my': mag[1],
				'mz': mag[2]}
				
				writer2.writerow(IMU2_data)
			
				time.sleep(0.01)
			else:
				print("Waiting for data")
				time.sleep(0.5)


if __name__ == '__main__':
	try:
		read2IMU()
	except (KeyboardInterrupt, SystemExit) as exErr:
		print("\nEnding imu_reader.py")
		sys.exit(0)
