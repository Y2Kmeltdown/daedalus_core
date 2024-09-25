import gpiozero
import smbus2
import time

addr = 0x67
WATCH_ON_OFF      = 0x01
WATCH_TIME        = 0x02
WATCH_REMAIN_TIME = 0x03
WATCH_STATE       = 0x04
WATCH_FwVersion   = 0x05

WATCH_ON  = 0x03
WATCH_OFF = 0x02

WATCH_Timeout = 0x03
WATCH_NO_Timeout = 0x02

WATCH_ON_LED = 0x10
WATCH_OFF_LED = 0x00

WATCH_version = 0x01

WATCH_TIME_Restart = 10

Feed_dogs = 4
try:
    bus = smbus2.SMBus(1)
    Feed_dogs = gpiozero.DigitalOutputDevice(Feed_dogs,active_high = True,initial_value =False)

    def read(address):
        data = bus.read_i2c_block_data(addr, address, 1)
        return data[0]

    def read_word(address):
        data = bus.read_i2c_block_data(addr, address, 2)
        return ((data[1] * 256 ) + data[0])

    def write(address,data):
        temp = [0]
        temp[0] = data & 0xFF
        bus.write_i2c_block_data(addr,address,temp)

    def write_word(address,data):
        temp = [0,0]
        temp[0] = data & 0xFF
        temp[1] =(data & 0xFF00) >> 8
        bus.write_i2c_block_data(addr,address,temp)


    if read(WATCH_FwVersion) == WATCH_version: #Access version number
        print("init succeed")
        write(WATCH_ON_OFF,WATCH_ON)#Enable watchdog function
        time.sleep(0.5)
        write(WATCH_STATE,WATCH_ON_LED | WATCH_NO_Timeout)  #Turn on the LED status indicator and clear the timeout flag
        write_word(WATCH_TIME,WATCH_TIME_Restart) #Set the timeout, currently 60 seconds

    else:
        print("init fail")

    while True:
        #Feed the dog every 0.8 seconds 0.8
        Feed_dogs.on()
        time.sleep(0.8)
        Feed_dogs.off()
        time.sleep(0.8)
    
except KeyboardInterrupt: 
    print("ctrl + c:")
    exit()
