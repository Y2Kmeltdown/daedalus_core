from smbus2 import SMBus
import csv
import argparse
import os
import sys
from datetime import datetime
import time

i2cbus = SMBus(1)
time.sleep(1)




def get_gps_burst(i2c_address) -> list[bytearray]:
    AvBytes_REG1 = 0xFD
    AvBytes_REG2 = 0xFE
    DataStream_REG = 0xFF
    GPS_Packet = []
    packet = bytearray()
    while(True):
        AvBytes1 = i2cbus.read_byte_data(i2c_address, AvBytes_REG1)
        AvBytes2 = i2cbus.read_byte_data(i2c_address, AvBytes_REG2)

        if AvBytes1 != 0 or AvBytes2 != 0:
            DataStream = i2cbus.read_byte_data(i2c_address, DataStream_REG)
            
            if DataStream == 36: # If value in data stream is "$" ascii character
                packet = bytearray()
                packet.append(DataStream)
            elif DataStream == 10: # If value in data stream is newline character "\n"
                GPS_Packet.append(packet)
                packet = bytearray()
            elif DataStream == 13: # If value in data stream is carriage return character "\r" if you want to remove carriage return edit this line
                packet.append(DataStream)
            else:
                packet.append(DataStream)
            
        elif GPS_Packet != []:
            break
    return GPS_Packet

def get_rmc(gps_burst: list[bytearray]):
    
    try:
        rmc = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNRMC') != -1][0] # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GNRMC" in it.

        print(rmc)
    except:
        rmc = None
    return rmc

def get_vtg(gps_burst: list[bytearray]):
    try:
        vtg = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNVTG') != -1][0] # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GNVTG" in it.
        print(vtg)
    except:
        vtg = None
    return vtg

def get_gga(gps_burst: list[bytearray]):
    try:
        gga = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGGA') != -1][0] # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GNGGA" in it.
        print(gga)
    except:
        gga = None
    return gga

def get_gll(gps_burst: list[bytearray]):
    try:
        gll = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGLL') != -1][0] # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GNGLL" in it.
        print(gll)
    except:
        gll = None
    
    return gll

def get_gsa(gps_burst: list[bytearray]):
    try:
        gsa = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGSA') != -1] # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GNGSA" in it.
        print(gsa)
    except:
        gsa = None
    return gsa

def get_gsv(gps_burst: list[bytearray]):
    try:
        gsv = {
            "gpgsv":[i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GPGSV') != -1], # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GPGSV" in it.
            "glgsv":[i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GLGSV') != -1], # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GLGSV" in it.
            "gagsv":[i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GAGSV') != -1], # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GAGSV" in it.
            "gbgsv":[i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GBGSV') != -1], # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GBGSV" in it.
            "gqgsv":[i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GQGSV') != -1]  # Decode bytes into utf-8 chars then split string using "," as a delimiter for any packet that contains the bytes b"$GQGSV" in it.
        }
        print(gsv)
    except:
        gsv = None
    return gsv

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("address", help="i2c Address for GPS", type=str)
    parser.add_argument(
		"--data_path",
		default=str("/usr/local/daedalus/data/gps"),
		help="Path to folder to save GPS data",
	)
    args = parser.parse_args()
    #i2cAddress = 0x42

    if not os.path.isdir(args.data_path):
        os.makedirs(args.data_path)
    start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
    filename = "gps-data_" + start_time + ".txt"
    with open(os.path.join(args.data_path, filename), 'w', newline='') as gpsfile:
        
        while(True):
            GPS_burst = get_gps_burst(int(args.address, 16))
            
            for packet in GPS_burst:
                gpsfile.write("%s\n" % packet.decode('utf-8'))
                print(f"{packet.decode('utf-8')}")
            #get_rmc(GPS_burst)
            #get_vtg(GPS_burst)
            #get_gga(GPS_burst)
            #get_gll(GPS_burst)
            #get_gsa(GPS_burst)
            #get_gsv(GPS_burst)

    
