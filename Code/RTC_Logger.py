#!/usr/bin/python
# -*- coding:utf-8 -*-
import serial
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
import RPi.GPIO as GPIO
import time
from waveshare_DS3231 import DS3231

str1  =["SUN","Mon","Tues","Wed","Thur","Fri","Sat"]
RTC = DS3231.DS3231(add = 0x68)

try:

    RTC.SET_Hour_Mode(24)
    RTC.SET_Time(23,59,50)
    RTC.SET_Day(7)  #RTC.SET_Day("Sat")
    RTC.SET_Calendar(2019,12,31)
    while(1):
        time.sleep(1)
        print("Day %s"%RTC.Read_Day_str())
        print (RTC.Read_Calendar())
        Time = RTC.Read_Time()
        print("hour : %d : %d : %d "%(Time[0],Time[1],Time[2]))
        print("hour : %x : %x : %x "%(RTC.Read_Time_Hour_BCD(),RTC.Read_Time_Min_BCD(),RTC.Read_Time_Sec_BCD()))
        print("temperature : %0.2f Celsius\r\n"%RTC.Read_Temperature())
            
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    exit()


     
     
     
     