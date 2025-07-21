from pymavlink import mavutil
import serial
import daedalus_utils
import argparse
import sys
import time

# Replace with your serial port and baud rate

def run(port:str, baud:int, datahandler:daedalus_utils.data_handler):
    ser = serial.Serial(port, baud)
    master = mavutil.mavlink_connection(ser.name)

    while True:
        msg = master.recv_match(blocking=True)
        if msg:
            datahandler.write_data(str(msg)+"\n")

if __name__ == "__main__":
    time.sleep(3) # Wait for socket server to start first
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--port",
        default="/dev/ttyUSB0",
        help="Serial Port for Cube Red", 
        type=str)
    parser.add_argument(
        "--data",
        default="/usr/local/daedalus/data",
        help="Path of the directory where recordings are stored",
        type=str
        )
    parser.add_argument(
        "--backup",
        default="/mnt/data",
        help="Path of the directory where recordings are backed up",
        type=str
        )
    parser.add_argument(
        "--socket",
        default=str("/tmp/telem.sock"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--record_time",
        default=300,
        type=int,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()
    
    baud = 115200

    telemDataHandler = daedalus_utils.data_handler(
        sensorName="telem", 
        extension = ".txt", 
        dataPath=args.data, 
        recordingTime=args.record_time,
        backupPath=args.backup,
        socketPath=args.socket
        )
    
    try:
        run(port=args.port, baud=baud,datahandler=telemDataHandler)
    except (KeyboardInterrupt, SystemExit):
        print("\nEnding telemetry_datalogger.py")
        sys.exit(0)
