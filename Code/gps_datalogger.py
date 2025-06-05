import serial
import argparse
from datetime import datetime, timedelta
import os
from pathlib import Path
import sys
import daedalus_utils

    
def checksumValidator(packet: bytearray) -> bool:
    checksum = 0
    for byte in packet[1:-4]:
        checksum ^= byte

    highNibbleAscii, lowNibbleAscii = ord(hex((checksum >> 4) & 0xf)[-1].capitalize()).to_bytes(1, 'big'), ord(hex((checksum) & 0xf)[-1].capitalize()).to_bytes(1, 'big')
    highInput, lowInput = packet[-3], packet[-2]

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

def run(serialPort, data_path, backup_path, record_time):
    port = serial.Serial(serialPort, baudrate=38400, timeout=1)

    gpsData = daedalus_utils.data_handler(
        sensorName=f"gps",
        extension=".txt",
        dataPath=data_path,
        backupPath=backup_path
        )
    
    buffer = []
    last_save_time = datetime.now()
    buffer_save_interval = timedelta(seconds=10)  # Save buffer every 10 seconds
    last_buffer_save = datetime.now()

    print("Starting data logging...")

    try:
        while True:
            gps_data = port.read(65535)
            nmeaPackets = gps_data.split(b"\n")

            for packet in nmeaPackets:
                if packet != b"":
                    packet, status, repair = packetRepairer(packet)

                    if status:
                        packet_data = packet + b'\n'
                        buffer.append(packet_data)

            # Save buffer to files every 10 seconds
            if datetime.now() - last_buffer_save >= buffer_save_interval and buffer:
                print(f"[INFO] Writing buffer at {datetime.now().strftime('%H:%M:%S')}...")
                
                gpsData.write_data(buffer)

                buffer.clear()  # Clear buffer after writing
                last_buffer_save = datetime.now()

            # Create a new file every 5 minutes
            if (datetime.now() - last_save_time).total_seconds() >= record_time:
                print(f"\n[INFO] Creating new file at {datetime.now().strftime('%H:%M:%S')}")
                last_save_time = datetime.now()
                gpsData.generate_filename()
                gpsData.validate_savepoints()

    except (ValueError, IOError) as err:
        print(f"[ERROR] {err}")
    finally:
        port.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("port", help="Serial Port for GPS", type=str)
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
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()


    try:
        run(args.port, args.data, args.backup, args.record_time)
    except (KeyboardInterrupt, SystemExit):
        print("\nEnding gps_reader.py")
        sys.exit(0)
