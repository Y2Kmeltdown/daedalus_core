from smbus2 import SMBus

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
    packerHeader = []
    rmc = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNRMC') != -1][0]
    print(rmc)

def get_vtg(gps_burst: list[bytearray]):
    packetHeader = []
    vtg = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNVTG') != -1][0]
    print(vtg)

def get_gga(gps_burst: list[bytearray]):
    packetHeader = []
    gga = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGGA') != -1][0]
    print(gga)

def get_gll(gps_burst: list[bytearray]):
    packetHeader = []
    gll = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGLL') != -1][0]
    print(gll)

def get_gsa(gps_burst: list[bytearray]):
    packetHeader = []
    gsa = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GNGSA') != -1]

def get_gsv(gps_burst: list[bytearray]):
    packetHeader = []
    gpgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GPGSV') != -1]
    glgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GLGSV') != -1]
    gagsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GAGSV') != -1]
    gbgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GBGSV') != -1]
    gqgsv = [i.decode("utf-8").split(",") for i in gps_burst if i.find(b'$GQGSV') != -1]
    

# packetHeader = [headers]
# byte.decode("utf-8")
# string.split(",")
# 

if __name__ == "__main__":
    while(True):
        GPS_burst = get_gps_burst()
        get_rmc(GPS_burst)
        get_vtg(GPS_burst)
        get_gga(GPS_burst)

    