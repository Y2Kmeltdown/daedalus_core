#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import logging
import argparse

logging.basicConfig(level=logging.INFO)
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
import time
from datetime import datetime
import csv
from waveshare_DS3231 import DS3231

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("i2c_address", help="i2c address for RTC", type=str)
parser.add_argument(
	"--data_path",
	default=str("/usr/local/daedalus/data/rtc"),
	help="Path to folder to save rtc data",
)
args = parser.parse_args()
dir_path = args.data_path

fieldnames = ['Timestamp', 'RTC_Date', 'RTC_Time', 'RTC_Temperature']

if not os.path.isdir(dir_path):
		os.makedirs(dir_path)

str1  =["Sun","Mon","Tues","Wed","Thur","Fri","Sat"]
RTC = DS3231.DS3231(add = int(args.i2c_address, 16))

start_time = datetime.now().strftime("%Y-%d-%m_%H-%M-%S")
filename = "RTC-data_" + start_time + ".csv"

with open(os.path.join(dir_path, filename), 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    try:
        timeNow = datetime.now()
        day = datetime.today().weekday()
        RTC.SET_Hour_Mode(24)
        RTC.SET_Time(timeNow.hour,timeNow.minute,timeNow.second)
        RTC.SET_Day(day)  #RTC.SET_Day("Sat")
        RTC.SET_Calendar(timeNow.year,timeNow.month,timeNow.day)
        while(1):
            time.sleep(1)
            RTC_data = {
                "Timestamp": datetime.now(),
                "RTC_Date": RTC.Read_Calendar(),
                "RTC_Time": RTC.Read_Time(),
                "RTC_Temperature": RTC.Read_Temperature()
            }
            writer.writerow(RTC_data)
            print("Day %s"%RTC.Read_Day_str())
            print (RTC.Read_Calendar())
            Time = RTC.Read_Time()
            print("hour : %d : %d : %d "%(Time[0],Time[1],Time[2]))
            print("hour : %x : %x : %x "%(RTC.Read_Time_Hour_BCD(),RTC.Read_Time_Min_BCD(),RTC.Read_Time_Sec_BCD()))
            print("temperature : %0.2f Celsius\r\n"%RTC.Read_Temperature())
                
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        exit()


     
     
     
     