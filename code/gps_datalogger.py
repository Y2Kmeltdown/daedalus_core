import argparse
import sys
import daedalus_utils
import time
    
def checksumValidator(packet: bytearray) -> bool:
    checksum = 0
    for byte in packet[1:-3]:
        checksum ^= byte
    
    highNibbleAscii, lowNibbleAscii = ord(hex((checksum >> 4) & 0xf)[-1].capitalize()).to_bytes(1, 'big'), ord(hex((checksum) & 0xf)[-1].capitalize()).to_bytes(1, 'big')
    highInput, lowInput = packet[-2], packet[-1]

    return highNibbleAscii == highInput.to_bytes(1, 'big') and lowNibbleAscii == lowInput.to_bytes(1, 'big')

def packetRepairer(packet: bytearray, repairLimit: int = 1) -> tuple[bytes, bool, bool]:
    valid = False
    repaired = False
    errors = []

    # Check for error bits in the packet
    for index, byte in enumerate(packet[1:-4]):
        if byte == 127:
            errors.append(index)

    if len(errors) == 0:  # If no error bits, validate checksum
        if checksumValidator(packet):
            return packet, True, False
        return packet, False, False

    if len(errors) <= repairLimit:  # Attempt to repair the packet
        testSolution = [44] * len(errors)
        bottomAscii, topAscii = 44, 90  # ASCII range
        asciiRange = topAscii - bottomAscii

        for _ in range(pow(asciiRange, len(errors))):
            testPacket = packet
            for errorIndex, errorFix in zip(errors, testSolution):
                testPacket = testPacket.replace(b'\x7F', errorFix.to_bytes(1, 'big'), 1)

            if checksumValidator(testPacket):
                return testPacket, True, True

            # Increment through ASCII combinations
            for index, testChar in enumerate(testSolution):
                if testChar == topAscii:
                    testSolution[index] = bottomAscii
                else:
                    testSolution[index] += 1
                    break

    return packet, False, False

def run(gpsTransciever:daedalus_utils.transceiver , gpsDataHandler:daedalus_utils.data_handler):
    #port = serial.Serial(serialPort, baudrate=38400, timeout=1)

    
    buffer = []
    print("Starting data logging...")

    try:
        while True:
            gps_data = gpsTransciever.receive()

            if gps_data:
                packet, status, repair = packetRepairer(gps_data)
                if status:
                    packet_data = packet + b'\r\n'
                    buffer.append(bytes(packet_data))
                    if packet_data[0:6] == b'$GNGLL':
                        gpsDataHandler.write_data(buffer)
                        buffer = []

    except (KeyboardInterrupt, SystemExit):
        print("Stopping GPS Reader.")


if __name__ == '__main__':
    time.sleep(3) # Wait for socket server to start first
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--port",
        default="/dev/ttyACM0",
        help="Serial Port for GPS", 
        type=str)
    parser.add_argument(
        "--data",
        default="/usr/local/daedalus/data",
        help="Path of the directory where recordings are stored",
    )
    parser.add_argument(
        "--backup",
        default="/mnt/data",
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--socket",
        default=str("/tmp/gps.sock"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--record_time",
        default=300,
        type=int,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()

    gpsDataHandler = daedalus_utils.data_handler(
        sensorName=f"gps",
        extension=".txt",
        dataPath=args.data,
        recordingTime=args.record_time,
        backupPath=args.backup,
        socketPath=args.socket
        )
    
    
    gpsTransciever = daedalus_utils.transceiver(args.port, 38400)

    try:
        run(gpsTransciever, gpsDataHandler)
    except (KeyboardInterrupt, SystemExit):
        print("\nEnding gps_datalogger.py")
        sys.exit(0)
