from smbus2 import SMBus
import time

i2cbus = SMBus(1)

i2cAddress = 0x42

AvBytes_REG1 = 0xFD
AvBytes_REG2 = 0xFE
DataStream_REG = 0xFF

count = 0
GPS_Packets = []
while(True):
    AvBytes1 = i2cbus.read_byte_data(i2cAddress, AvBytes_REG1)
    AvBytes2 = i2cbus.read_byte_data(i2cAddress, AvBytes_REG2)

    if AvBytes1 != 0 or AvBytes2 != 0:
        DataStream = i2cbus.read_byte_data(i2cAddress, DataStream_REG)

        #with open("test.txt", "ab") as file:
            #file.write(DataStream.to_bytes(1, 'big'))
        
        if DataStream == 36:
            packet = bytearray()
            packet.append(DataStream)
        elif DataStream == 10:
            GPS_Packets.append(packet)
            packet = bytearray
            count+=1
        elif DataStream == 13:
            pass
        else:
            packet.append(DataStream)
        
        if len(GPS_Packets) >= 50:
            break

print(GPS_Packets)
            

    