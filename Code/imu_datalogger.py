# #!/usr/bin/env python
# #-----------------------------------------------------------------------------
# # imu_reader.py
# #
# # Script to read data over I2C from two ICM20948 boards using the Adafruit ICM libraries
# #
# #==================================================================================

# import time
# from datetime import datetime
# import sys
# import csv
# import os
# import argparse
# from pathlib import Path
# import board
# import adafruit_icm20x

# ADDRESS_1 = 0x69
# ADDRESS_2 = 0x68

# def readIMU(i2c_address, dir_path):
# 	counter = 0
	
# 	i2c = board.I2C()  # uses board.SCL and board.SDA

# 	icm = adafruit_icm20x.ICM20948(i2c,i2c_address)

# 	print("\nDaedalus IMU Reader\n")

# 	fieldnames = ['Timestamp', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz']

# 	if not os.path.isdir(dir_path):
# 		os.makedirs(dir_path)

# 	print(dir_path)

# 	start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
# 	filename = "imu-data_" + start_time + ".csv"
	
# 	with open(os.path.join(dir_path, filename), 'w', newline='') as csvfile:
# 		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
# 		writer.writeheader()
			
# 		while True:
# 			# print("Writing data...")
			
# 			# Update and write data from first IMU
# 			accel = icm.acceleration
# 			gyro = icm.gyro
# 			mag = icm.magnetic
			
# 			IMU_data = {'Timestamp': datetime.now(),
# 			'ax': accel[0], 
# 			'ay': accel[1], 
# 			'az': accel[2],
# 			'gx': gyro[0],
# 			'gy': gyro[1],
# 			'gz': gyro[2],
# 			'mx': mag[0],
# 			'my': mag[1],
# 			'mz': mag[2]}
			
# 			writer.writerow(IMU_data)
# 			counter+=1
# 			if counter == 100:
# 				print(IMU_data, flush=True) 
# 				counter = 0
		
# 			time.sleep(0.01)


# if __name__ == '__main__':

# 	parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# 	parser.add_argument("i2c_address", help="I2C address for IMU", type=str)
# 	parser.add_argument(
# 		"--data",
# 		default=str(Path.home() / 'data/imu_horizon'),
# 		help="Path to folder to save IMU data",
# 	)
# 	parser.add_argument(
#     "--backup",
#     default=str("/mnt/data"),
#     help="Path of the directory where recordings are backed up",
# 	)
# 	args = parser.parse_args()

# 	try:
# 		readIMU(int(args.i2c_address, 16), args.data)
# 	except (KeyboardInterrupt, SystemExit) as exErr:
# 		print("\nEnding imu_reader.py")
# 		sys.exit(0)


#!/usr/bin/env python
# imu_datalogger.py
# Script to read data over I2C from an ICM20948 board using the Adafruit ICM libraries
import time
from datetime import datetime
import argparse
from pathlib import Path
import board
import os
import adafruit_icm20x

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
    i2c = board.I2C()  # uses board.SCL and board.SDA
    icm = adafruit_icm20x.ICM20948(i2c, i2c_address)
    print("Starting IMU Reader...")

    ensure_directory_exists(data_path)
    ensure_directory_exists(backup_path)

    data_file_sd = generate_file_name(data_path)
    data_file_usb = generate_file_name(backup_path)
    usb_connected = True

    try:
        while True:
            accel = icm.acceleration
            gyro = icm.gyro
            mag = icm.magnetic
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data_line = f"{timestamp}\tax:{accel}\tgy:{gyro}\tmag:{mag}\n"
            
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
