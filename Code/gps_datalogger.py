import serial
import argparse
from datetime import datetime
import csv
import sys
import os

def checksumValidator(packet:bytearray) -> bool:
  checksum = 0
  for byte in packet[1:-5]:
    checksum ^= byte

  highNibbleAscii, lowNibbleAscii = ord(hex((checksum >> 4) & 0xf)[-1]).to_bytes(1, 'big'), ord(hex((checksum) & 0xf)[-1]).to_bytes(1, 'big')
  highInput, lowInput = packet[-4], packet[-3]

  if highNibbleAscii == highInput.to_bytes(1,'big') and lowNibbleAscii == lowInput.to_bytes(1,'big'):
    return True
  else:
    return False

def packetRepairer(packet:bytearray, repairLimit:int=1) -> tuple[bytes, bool, bool] :
  """
  """
  valid = False
  repaired = False
  errors = []

  # Check for how many error bits are in packet
  for index, byte in enumerate(packet[1:-4]):
    if byte == 127:
      errors.append(index)

  if len(errors) == 0: # If no error bits are detected do a checksum validation
    if checksumValidator: # If checksum is good return original packet and stats
      outPacket = packet
      valid = True
      repaired = False
    else: # if checksum is bad return original packet and fail
      outPacket = packet
      valid = False
      repaired = False

  if len(errors) <= repairLimit: # If number of errors is lower than set repair limit attempt to repair the packet
    testSolution = [44]*len(errors)
    bottomAscii = 44 # ","
    topAscii = 90 # "Z"
    asciiRange = topAscii-bottomAscii

    for i in range(pow(asciiRange,len(errors))): # Repair is O^n complexity due to needing to search for a solution through all available values.

      #Test replacing error bits with test bits then check validation
      testPacket = packet
      for errorIndex, errorFix in zip(errors,testSolution):
        testPacket = testPacket.replace(b'\x7F', errorFix.to_bytes(1,'big'), 1)
              
      if checksumValidator(testPacket):
        outPacket = testPacket
        valid = True
        repaired = True
        return outPacket, valid, repaired
              
        #Increment through ascii bits combinations
      for index, testChar in enumerate(testSolution):
        if index == 0:
          if testChar == topAscii:
            testSolution[index] = bottomAscii
          else:
            testSolution[index] +=1
        else:
          if testSolution[index-1] == topAscii:
            if testChar == topAscii:
              testSolution[index] = bottomAscii
            else:
              testSolution[index] +=1
          # If no solutions are found return original packet and fail
    valid = False
    repaired = False
    outPacket = packet
              
  else: # If number of errors are above repair limit give up life is hopeless
    valid = False
    repaired = False
    outPacket = packet


  return outPacket, valid, repaired

def run(serialPort, dir_path):

  port = serial.Serial(serialPort, baudrate=38400, timeout=1)

  fieldnames = ['Timestamp', 'Latitude', 'Longitude', 'Heading', 'UTC_Date', "UTC_Time"]

  if not os.path.isdir(dir_path):
    os.makedirs(dir_path)
  start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
  filename = "gps-data_" + start_time + ".csv"
  
  #######################TODO Make it open a second location###########################
  with open(os.path.join(dir_path, filename), 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    try: 
      print("Listening for UBX Messages.")
      while True:
        try: 
          gps_data = port.read(65535)

          print(gps_data)

          ###################TODO WRITE GPS COLLECTION SCRIPT##########################
          #writer.writerow(GPS_data)
          #print(GPS_data, flush=True)
          #############################################################################          

        except (ValueError, IOError) as err:
          print(err)
    
    finally:
      port.close()

if __name__ == '__main__':
  parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("port", help="Serial Port for GPS", type=str)
  parser.add_argument(
		"--data",
		default=str("/usr/local/daedalus/data/gps"),
		help="Path to folder to save GPS data",
	)
  parser.add_argument(
    "--backup",
    default=str("/usr/local/daedalus/data"),
    help="Path of the directory where recordings are backed up",
  )
  args = parser.parse_args()
  #/dev/ttyAMA0
  
  try:
    run(args.port, args.data)
  except (KeyboardInterrupt, SystemExit) as exErr:
    print("\nEnding gps_reader.py")
    sys.exit(0)