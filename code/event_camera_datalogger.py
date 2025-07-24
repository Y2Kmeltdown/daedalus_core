import argparse
import dataclasses
import json
import time
import sys
from threading import Thread, Lock
import os
import logging

import daedalus_utils
import neuromorphic_drivers as nd

logging.basicConfig()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("server")
log_level = getattr(logging, log_level)
logger.setLevel(log_level)


class eventCamera(Thread):
    def __init__(
            self, 
            serial:str,
            configuration:nd.prophesee_evk4.Configuration, 
            eventDataHandler:daedalus_utils.data_handler,
            measureDataHandler:daedalus_utils.data_handler,
            metaDataHandler:daedalus_utils.data_handler,
            raw:bool = False, 
            measurementInterval:float = 0.1
            ):
        super().__init__(daemon=True)

        self.configuration = configuration
        self.eventDataHandler = eventDataHandler
        self.measureDataHandler = measureDataHandler
        self.metaDataHandler = metaDataHandler
        self.serial = serial
        self.raw = raw
        self.measurementInterval = int(round(measurementInterval * 1e9))
        self.metadata_json = None
        self.eventList = []
        self.measurementList = []
        self.sampleList = []
        
    
    def run(self):
        with nd.open(raw=self.raw, serial=self.serial, configuration=self.configuration) as device:
            print(f"[INFO] Successfully started EVK4 at serial: {self.serial}", flush=True)
            # Save the camera biases (metadata)
            metadata = {
                "system_time": time.time(),
                "properties": dataclasses.asdict(device.properties()),
                "configuration": str(self.configuration),
            }
            self.metadata_json = json.dumps(metadata, indent=4)
            events_cursor = 0
            start_time = time.monotonic_ns()
            next_measurement = start_time
            for status, packet in device:
                #print(packet.keys())
                if self.raw == False:
                    events = packet["dvs_events"].tolist()
                else:
                    events = packet

                with data_lock:
                    self.eventList.append(events)
                events_cursor += len(packet)
                # Prepare sample data
                try:
                    status_dict = dataclasses.asdict(status)
                    status_dict["events_cursor"] = events_cursor
                    sample_line = json.dumps(status_dict).encode() + b'\n'
                    with data_lock:
                        self.sampleList.append(sample_line.decode("utf-8"))
                    
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
                        with data_lock:
                            self.measurementList.append(measurement_line.decode("utf-8"))
                    except Exception as e:
                        print(f"Error obtaining measurements: {e}", file=sys.stderr)

                    next_measurement = time.monotonic_ns() + self.measurementInterval

    def getMetadata(self):
        while not self.metadata_json:
            pass
        self.metaDataHandler.write_data(self.metadata_json, now=True)
        return self.metadata_json
    
    def getEventBuffer(self):
        with data_lock:
            events = self.eventList
            measurements = self.measurementList
            samples = self.sampleList
            self.eventList = []
            self.measurementList = []
            self.sampleList = []
            measurementData = {
                "measurements": measurements,
                "samples": samples
            }
            self.measureDataHandler.write_data(json.dumps(measurementData,indent=None)+"\n")
            self.eventDataHandler.write_data(events)
        return events
    
def check_event_camera(serialNumberList):
    evkSerialList = [i.serial for i in nd.list_devices()]
    try:
        serialNumbers = [i for i in evkSerialList if i in serialNumberList]
        return serialNumbers
    except Exception as e:
        print(f"Error during serial number check: {e}", flush=True)
        return None
    

if __name__ == "__main__":
    time.sleep(3) # Wait for socket server to start first
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--serial", 
        default="",
        help="Camera serial number list. Will start recording data from all specified cameras if they are connected (for example 00050423 00051505 00051503).\nIf none are specified the first available camera will be used.",
        nargs="+",
        type=str
    )
    
    parser.add_argument(
        "--data",
        default="/home/daedalus/daedalus_core/data",
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
    parser.add_argument(
        "--socket",
        default=str("/tmp/event.sock"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--record_time",
        default=300,
        type=int,
        help="Time in seconds for how long to record to a single file"
    )
    parser.add_argument(
        "--diff_on",
        default=140,
        type=int,
        help="Event Camera On Bias"
    )
    parser.add_argument(
        "--diff_off",
        default=80,
        type=int,
        help="Event Camera Off Bias"
    )
    args = parser.parse_args()

    # INITIALISE EVENT CAMERAS

    data_lock = Lock()

    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=args.diff_off,  # default: 102
            diff_on=args.diff_on,    # default: 73
        )
    )

    if args.serial == "":
        evkSerialList = [i.serial for i in nd.list_devices()]
    else:
        evkSerialList = check_event_camera(args.serial)

    if evkSerialList:
        serial = evkSerialList[0]
        eventCameraDict = {}
        metadataList = []
        eventData = daedalus_utils.data_handler(
            sensorName=f"evk4_{serial}",
            extension=".raw",
            dataPath=args.data,
            backupPath=args.backup,
            recordingTime=args.record_time,
            socketPath=args.socket
            )
        eventMeasurements = daedalus_utils.data_handler(
            sensorName=f"evk4_{serial}_measurements",
            extension=".jsonl",
            dataPath=args.data,
            backupPath=args.backup,
            recordingTime=args.record_time
            )
        eventMetadata = daedalus_utils.data_handler(
            sensorName=f"evk4_{serial}_metadata",
            extension=".json",
            dataPath=args.data,
            backupPath=args.backup,
            recordingTime=args.record_time
            )
        raw = True
        camera = eventCamera(
            serial=serial, 
            configuration=configuration, 
            eventDataHandler=eventData,
            metaDataHandler=eventMetadata,
            measureDataHandler=eventMeasurements,
            raw=raw, 
            measurementInterval=args.measurement_interval
            )
    else:
        print("[INFO] No Event Cameras connected to system.", flush=True)

    
    try:
        print("[INFO] Starting Camera")
        camera.start()
        camMetadata = camera.getMetadata()
        

        while True:
            time.sleep(0.01)
            camera.getEventBuffer()

    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")