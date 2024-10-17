from ublox_gps import UbloxGps
import serial
import argparse
from datetime import datetime
import csv
import sys
import os



def run(serialPort, dir_path):

  port = serial.Serial(serialPort, baudrate=38400, timeout=1)
  gps = UbloxGps(port)

  fieldnames = ['Timestamp', 'Latitude', 'Longitude', 'Heading', 'UTC_Date', "UTC_Time"]

  if not os.path.isdir(dir_path):
    os.makedirs(dir_path)
  start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
  filename = "gps-data_" + start_time + ".csv"
  
  with open(os.path.join(dir_path, filename), 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    try: 
      print("Listening for UBX Messages.")
      while True:
        try: 
          coords = gps.geo_coords()
          gps_datetime = gps.date_time()

          GPS_data = {"Timestamp": datetime.now(),
          "UTC_Date":f"{gps_datetime.year}-{gps_datetime.month}-{gps_datetime.day}",
          "UTC_Time":f"{gps_datetime.hour}-{gps_datetime.min}-{gps_datetime.sec}",
          "Latitude":coords.lat,
          "Longitude":coords.lon,
          "Heading":coords.headMot
          }
          writer.writerow(GPS_data)
          print(GPS_data, flush=True) 
          

        except (ValueError, IOError) as err:
          print(err)
    
    finally:
      port.close()

if __name__ == '__main__':
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("port", help="Serial Port for GPS", type=str)
  parser.add_argument(
		"--data_path",
		default=str("/usr/local/daedalus/data/gps"),
		help="Path to folder to save GPS data",
	)
  parser.add_argument(
    "--backups",
    default=str("/usr/local/daedalus/data"),
    help="Path of the directory where recordings are backed up",
  )
  args = parser.parse_args()
  #/dev/ttyAMA0
  
  try:
    run(args.port, args.data_path)
  except (KeyboardInterrupt, SystemExit) as exErr:
    print("\nEnding gps_reader.py")
    sys.exit(0)