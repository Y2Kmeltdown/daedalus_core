from smbus2 import SMBus
import csv
import argparse
import os
import sys
from datetime import datetime
import time

i2cbus = SMBus(1)
time.sleep(1)

reset_REG = 0xE0
reset_WORD = 0xB6

ctrl_hum_REG = 0xF2
ctrl_hum_WORD = 0x02

ctrl_meas_REG = 0xF4
ctrl_meas_WORD = 0x27


i2c_address = 0x77

status_REG = 0xF3

press_msb_REG = 0xF7
press_lsb_REG = 0xF8
press_xlsb_REG = 0xF9

temp_msb_REG = 0xFA
temp_lsb_REG = 0xFB
temp_xlsb_REG = 0xFC

hum_msb_REG = 0xFD
hum_lsb_REG = 0xFE

def testRead(i2c_address):
    i2cbus.write_byte_data(i2c_address,reset_REG,reset_WORD)

    i2cbus.write_byte_data(i2c_address,ctrl_hum_REG,ctrl_hum_WORD)
    i2cbus.write_byte_data(i2c_address,ctrl_meas_REG,ctrl_meas_WORD)
    
    while(True):
        status_data = i2cbus.read_byte_data(i2c_address,status_REG)
        print(status_data)
        time.sleep(0.1)
        if status_data == 0:
            pressure = [
                i2cbus.read_byte_data(i2c_address,press_msb_REG),
                i2cbus.read_byte_data(i2c_address,press_lsb_REG),
                i2cbus.read_byte_data(i2c_address,press_xlsb_REG)
            ]
            temperature = [
                i2cbus.read_byte_data(i2c_address,temp_msb_REG),
                i2cbus.read_byte_data(i2c_address,temp_lsb_REG),
                i2cbus.read_byte_data(i2c_address,temp_xlsb_REG)
            ]
            humidity = [
                i2cbus.read_byte_data(i2c_address,hum_msb_REG),
                i2cbus.read_byte_data(i2c_address,hum_lsb_REG)
            ]
            print(pressure)
            print(temperature)
            print(humidity)
        

if __name__ == "__main__":
    testRead(i2c_address)

