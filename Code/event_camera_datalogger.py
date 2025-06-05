import argparse
import dataclasses
import datetime
import pathlib
import json
import time
import sys

import daedalus_utils
import neuromorphic_drivers as nd

def check_event_camera(serialNumberList):
    evkSerialList = [i.serial for i in nd.list_devices()]
    try:
        serialNumber = [i for i in evkSerialList if i in serialNumberList][0]
        return serialNumber
    except Exception as e:
        print(f"Error during serial number check: {e}", flush=True)
        return None
    
def record_5Mins(serial:str):

    

    start_recording = time.monotonic_ns()
    end_recording = start_recording + 300_000_000_000
    flush_interval = int(round(args.flush_interval * 1e9))
    measurement_interval = int(round(args.measurement_interval * 1e9))
    name = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    with nd.open(raw=True, serial=serial) as device:
        print(f"Successfully started EVK4 at serial: {serial}")

        # Save the camera biases (metadata)
        metadata = {
            "system_time": time.time(),
            "properties": dataclasses.asdict(device.properties()),
            "configuration": "NONE",
        }
        metadata_json = json.dumps(metadata, indent=4)
        eventMetadata.write_data(metadata_json)

        events_cursor = 0
        start_time = time.monotonic_ns()
        next_measurement = start_time

        for status, packet in device:
            eventData.write_data(packet)
            events_cursor += len(packet)

            # Prepare sample data
            try:
                status_dict = dataclasses.asdict(status)
                status_dict["events_cursor"] = events_cursor
                sample_line = json.dumps(status_dict).encode() + b'\n'

                eventSamples.write_data(sample_line)
                
            except Exception as e:
                print(f"Error processing sample data: {e}", file=sys.stderr)

            # Measurements at intervals
            if time.monotonic_ns() >= next_measurement:
                try:
                    measurement_dict = {
                        "system_time": time.time(),
                        "temperature": device.temperature_celsius(),
                        "illuminance": device.illuminance(),
                    }
                    measurement_line = json.dumps(measurement_dict).encode() + b'\n'

                    eventMeasurements.write_data(measurement_line)
                except Exception as e:
                    print(f"Error obtaining measurements: {e}", file=sys.stderr)

                next_measurement = time.monotonic_ns() + measurement_interval

            # Check if recording time is over
            if time.monotonic_ns() >= end_recording:
                eventData.generate_filename()
                eventData.validate_savepoints()

                eventMetadata.generate_filename()
                eventMetadata.validate_savepoints()

                eventSamples.generate_filename()
                eventSamples.validate_savepoints()

                eventMeasurements.generate_filename()
                eventMeasurements.validate_savepoints()
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "serial", 
        help="Camera serial number list must contain at least one serial number (for example 00050423 00051505 00051503)",
        nargs="+",
        type=str
    )
    parser.add_argument(
        "--data",
        default="/usr/local/daedalus/data",
        help="Path of the directory where recordings are stored",
    )
    parser.add_argument(
        "--backup",
        default=str("/mnt/data"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--measurement-interval",
        default=0.1,
        type=float,
        help="Interval between temperature and illuminance measurements in seconds",
    )
    parser.add_argument(
        "--flush-interval",
        default=0.5,
        type=float,
        help="Maximum interval between file flushes in seconds",
    )
    args = parser.parse_args()

    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=102,  # default: 102
            diff_on=73,    # default: 73
        )
    )
    serial = check_event_camera(args.serial)

    eventData = daedalus_utils.data_handler(
        sensorName=f"evk4_{serial}",
        extension=".es",
        dataPath=args.data,
        backupPath=args.backup
        )
    
    eventMetadata = daedalus_utils.data_handler(
        sensorName=f"evk4_{serial}_metadata",
        extension=".json",
        dataPath=args.data,
        backupPath=args.backup
        )
    
    eventSamples = daedalus_utils.data_handler(
        sensorName=f"evk4_{serial}_samples",
        extension=".jsonl",
        dataPath=args.data,
        backupPath=args.backup
        )
    
    eventMeasurements = daedalus_utils.data_handler(
        sensorName=f"evk4_{serial}_measurements",
        extension=".jsonl",
        dataPath=args.data,
        backupPath=args.backup
        )

    while True:
        record_5Mins(serial)
