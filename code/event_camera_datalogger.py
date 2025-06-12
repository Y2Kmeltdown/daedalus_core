import argparse
import dataclasses
import datetime
import pathlib
import json
import time
import sys
from threading import Thread, Lock
import os
import socket
import queue

import daedalus_utils
import neuromorphic_drivers as nd

# eventList = []
# measurementList = []
# sampleList = []
class eventCamera(Thread):
    def __init__(self, serial:str,configuration:nd.prophesee_evk4.Configuration, raw:bool = False, measurementInterval:float = 0.1):
        super().__init__(daemon=True)
        self.configuration = configuration
        self.serial = serial
        self.raw = raw
        self.measurementInterval = int(round(measurementInterval * 1e9))
        self.metadata_json = None
        self.eventList = []
        self.measurementList = []
        self.sampleList = []
        
    
    def run(self):
        # global eventList
        # global sampleList
        # global measurementList
        with nd.open(raw=self.raw, serial=self.serial, configuration=self.configuration) as device:
            print(f"INFO: Successfully started EVK4 at serial: {serial}")
            # Save the camera biases (metadata)
            metadata = {
                "system_time": time.time(),
                "properties": dataclasses.asdict(device.properties()),
                "configuration": "NONE",
            }
            self.metadata_json = json.dumps(metadata, indent=4)
            #eventMetadataHandler.write_data(metadata_json, now=True)
            events_cursor = 0
            start_time = time.monotonic_ns()
            next_measurement = start_time
            for status, packet in device:
                with data_lock:
                    self.eventList.append(packet)
                events_cursor += len(packet)
                # Prepare sample data
                try:
                    status_dict = dataclasses.asdict(status)
                    status_dict["events_cursor"] = events_cursor
                    sample_line = json.dumps(status_dict).encode() + b'\n'
                    with data_lock:
                        self.sampleList.append(sample_line)
                    
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
                            self.measurementList.append(measurement_line)
                    except Exception as e:
                        print(f"Error obtaining measurements: {e}", file=sys.stderr)

                    next_measurement = time.monotonic_ns() + self.measurementInterval

    def getMetadata(self):
        while not self.metadata_json:
            pass
        return self.metadata_json
    
    def getEventBuffer(self):
        #global eventList
        with data_lock:
            events = self.eventList
            measurements = self.measurementList
            samples = self.sampleList
            self.eventList = []
            self.measurementList = []
            self.sampleList = []
        return events, measurements, samples
    

class socketServer(Thread):
    def __init__(self, name:str, socketFile:any, socketQueue:queue.Queue):
        super().__init__(daemon=True)

        self.name = name

        if type(socketFile) is pathlib.Path:
            self.socketFile = socketFile
        elif type(socketFile) is str:
            self.socketFile = pathlib.Path(socketFile)
        elif type(socketFile) is bytes:
            self.socketFile = pathlib.Path(str(socketFile))
        else:
            raise Exception("socketFile must be a Path, String or Bytes object")

        self.socketQueue = socketQueue
        

    def run(self):
        if os.path.exists(str(self.socketFile)):
            os.remove(str(self.socketFile))

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socketFile))
        while True:
            server.listen(1)
            conn, addr = server.accept()
            data = conn.recv(2048)
    
            if data is not None:
                self.socketQueue.put(data)
                self.socketQueue.task_done()


def check_event_camera(serialNumberList):
    evkSerialList = [i.serial for i in nd.list_devices()]
    try:
        serialNumbers = [i for i in evkSerialList if i in serialNumberList]
        return serialNumbers
    except Exception as e:
        print(f"Error during serial number check: {e}", flush=True)
        return None
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--serial", 
        default="",
        help="Camera serial number list. Will start recording data from all specified cameras if they are connected. If  (for example 00050423 00051505 00051503)",
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
    parser.add_argument(
        "--record_time",
        default=300,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()

    data_lock = Lock()

    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=102,  # default: 102
            diff_on=73,    # default: 73
        )
    )

    supervisorFile = "config/supervisord.conf"
    eventide = daedalus_utils.supervisor(supervisorFile)
    eventideDataHandler = daedalus_utils.data_handler(
        sensorName=f"event_synced",
        extension=".json",
        dataPath=args.data,
        backupPath=args.backup,
        recordingTime=args.record_time
        )
    
    # Socket Handler
    socketDict = {}
    for key, supervisorObject in eventide.moduleDict.items():
        sock = supervisorObject.sock
        if sock is not None:
            socketQueue = queue.Queue()
            socketFile = str(sock)
            socketThread = socketServer(key, socketFile=socketFile, socketQueue=socketQueue)
            socketThread.start()
            socketDict[key] = (socketFile, socketQueue, socketThread)

    print(socketDict)

    if args.serial == "":
        evkSerialList = [i.serial for i in nd.list_devices()]
    else:
        evkSerialList = check_event_camera(args.serial)
    
    if evkSerialList:
        eventCameraDict = {}
        for serial in evkSerialList:
            camera = eventCamera(serial, configuration, False, measurementInterval=args.measurement_interval)
            camera.start()
            eventCameraDict[serial] = camera
            print(camera.getMetadata())
    else:
        print("INFO: No Event Cameras connected to system.")

    testSerial = "00051501"

    while True:
        data = eventCameraDict[testSerial].getEventBuffer()
        print(len(data[0]))
        print(len(data[1]))
        print(len(data[2]))
        time.sleep(1)
        
