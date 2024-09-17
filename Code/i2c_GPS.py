from smbus2 import SMBus
import csv
import argparse
import os
import sys

i2cbus = SMBus(1)

i2cAddress = 0x42

AvBytes_REG1 = 0xFD
AvBytes_REG2 = 0xFE
DataStream_REG = 0xFF

def get_gps_burst() -> list[bytearray]:
    GPS_Packet = []
    packet = bytearray()
    while(True):
        AvBytes1 = i2cbus.read_byte_data(i2cAddress, AvBytes_REG1)
        AvBytes2 = i2cbus.read_byte_data(i2cAddress, AvBytes_REG2)

        if AvBytes1 != 0 or AvBytes2 != 0:
            DataStream = i2cbus.read_byte_data(i2cAddress, DataStream_REG)
            
            if DataStream == 36: # If value in data stream is $ ascii character
                packet = bytearray()
                packet.append(DataStream)
            elif DataStream == 10: # If value in data stream is newline character "\n"
                GPS_Packet.append(packet)
                packet = bytearray()
            elif DataStream == 13: # If value in data stream is carriage return character "\r"
                pass
            else:
                packet.append(DataStream)
            
        elif GPS_Packet != []:
            break
    return GPS_Packet

def get_rmc(gps_burst: list[bytearray]):
    
    try:
        rmc = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNRMC') != -1][0]

        print(rmc)
    except:
        pass

def get_vtg(gps_burst: list[bytearray]):
    try:
        vtg = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNVTG') != -1][0]
        print(vtg)
    except:
        pass

def get_gga(gps_burst: list[bytearray]):
    try:
        gga = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGGA') != -1][0]
        print(gga)
    except:
        pass

def get_gll(gps_burst: list[bytearray]):
    try:
        gll = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGLL') != -1][0]
        print(gll)
    except:
        pass

def get_gsa(gps_burst: list[bytearray]):
    try:
        gsa = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGSA') != -1]
    except:
        pass

def get_gsv(gps_burst: list[bytearray]):
    try:
        gpgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GPGSV') != -1]
        glgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GLGSV') != -1]
        gagsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GAGSV') != -1]
        gbgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GBGSV') != -1]
        gqgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GQGSV') != -1]
    except:
        pass
    

if __name__ == "__main__":
    while(True):
        GPS_burst = get_gps_burst()
        #print(GPS_burst)
        get_rmc(GPS_burst)
        get_vtg(GPS_burst)
        get_gga(GPS_burst)
        get_gll(GPS_burst)
        get_gsa(GPS_burst)
        get_gsv(GPS_burst)

    