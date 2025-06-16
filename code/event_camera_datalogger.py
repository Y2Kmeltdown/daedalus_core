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
import base64

import daedalus_utils
import neuromorphic_drivers as nd
import numpy


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
        with nd.open(raw=self.raw, serial=self.serial, configuration=self.configuration) as device:
            print(f"[INFO] Successfully started EVK4 at serial: {self.serial}", flush=True)
            # Save the camera biases (metadata)
            metadata = {
                "system_time": time.time(),
                "properties": dataclasses.asdict(device.properties()),
                "configuration": "NONE",
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
                    events = base64.b64encode(packet).decode("utf-8")

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
        return self.metadata_json
    
    def getEventBuffer(self):
        with data_lock:
            events = self.eventList
            measurements = self.measurementList
            samples = self.sampleList
            self.eventList = []
            self.measurementList = []
            self.sampleList = []
            eventData = {
                "events": events,
                "measurements": measurements,
                "samples": samples
            }
        return eventData
    

class socketServer(Thread):
    def __init__(self, name:str, socketFile:any, socketQueue:queue.Queue, buffer:bool = False, bufsize:int = 4096):
        super().__init__(daemon=True)

        self.name = name

        self.dataList = []

        if type(socketFile) is pathlib.Path:
            self.socketFile = socketFile
        elif type(socketFile) is str:
            self.socketFile = pathlib.Path(socketFile)
        elif type(socketFile) is bytes:
            self.socketFile = pathlib.Path(str(socketFile))
        else:
            raise Exception("socketFile must be a Path, String or Bytes object")

        self.bufsize = bufsize

        self.buffer = buffer
        if buffer:
            self.socketList = []
        else:
            self.socketQueue = socketQueue
        

    def run(self):
        if os.path.exists(str(self.socketFile)):
            os.remove(str(self.socketFile))

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            
            s.bind(str(self.socketFile))
            s.listen(1)
            while True:
                conn, addr = s.accept()
                print(f"[INFO] {self.name} socket connected.", flush=True)
                socketBuffer = []
                while True:
                    data = conn.recv(self.bufsize)
                    
                    if data[-5:] == b"EOT\x03\x04":
                        socketBuffer.append(data[:-5])
                        #print("[INFO] EOT Detected")
                        
                        socketOut = b"".join(socketBuffer)
                        socketBuffer = []
                        if self.buffer:
                            with data_lock:
                                self.dataList.append(socketOut)
                        else:
                            self.socketQueue.put(socketOut)
                            self.socketQueue.task_done()
                    elif data is not b"":
                        socketBuffer.append(data)
                        #print(data[-5:])
                    elif data is b"":
                        print(f"[WARNING] {self.name} socket disconnected. Attempting to reconnect.")
                        break
                    
                    


    def getDataBuffer(self):
        if self.buffer:
            with data_lock:
                data = self.dataList
                self.dataList = []
            return data
        else:
            return None




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
        default="/home/eventide/daedalus_core/data",
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


    # INITIAL SUPERVISOR ACCESS AND DATA HANDLER
    supervisorFile = "../config/supervisord.conf"
    eventide = daedalus_utils.supervisor(supervisorFile)
    eventideDataHandler = daedalus_utils.data_handler(
        sensorName=f"event_synced",
        extension=".jsonl",
        dataPath=args.data,
        backupPath=args.backup,
        recordingTime=args.record_time
        )
    
    # INITIALISE SOCKET SERVERS

    # Socket Handler
    socketDict = {}
    for key, supervisorObject in eventide.moduleDict.items():
        sock = supervisorObject.sock
        if sock is not None:
            socketQueue = queue.Queue()
            socketFile = str(sock)
            if key == "g_p_s":# or key == "pi_picture_camera":
                buffer = False
                bufsize = 4096
            elif key == "pi_picture_camera":
                buffer = False
                bufsize = 32768
            elif key == "infra_red_camera":
                buffer = False
                bufsize = 32768
            else:
                buffer = True
                bufsize = 4096
            socketThread = socketServer(key, socketFile=socketFile, socketQueue=socketQueue, buffer=buffer, bufsize=bufsize)
            socketThread.start()
            socketDict[key] = (socketFile, socketQueue, socketThread)

    #print(socketDict)

    # INITIALISE EVENT CAMERAS

    data_lock = Lock()

    configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=102,  # default: 102
            diff_on=73,    # default: 73
        )
    )

    if args.serial == "":
        evkSerialList = [i.serial for i in nd.list_devices()]
    else:
        evkSerialList = check_event_camera(args.serial)
    
    if evkSerialList:
        eventCameraDict = {}
        metadataList = []
        for serial in evkSerialList:
            raw = True
            camera = eventCamera(serial=serial, configuration=configuration, raw=raw, measurementInterval=args.measurement_interval)
            camera.start()
            camMetadata = camera.getMetadata()
            eventCameraDict[serial] = camera
            metadataList.append(camMetadata)
            metadataList.append({"raw":raw})
    else:
        print("[INFO] No Event Cameras connected to system.", flush=True)

    # RUN CODE

    testSerial = "00051501"
    eventideList = []
    GPS_data = ""
    while True:
        try:
            piPicData = socketDict["pi_picture_camera"][1].get_nowait()
            base64PiImage = base64.b64encode(piPicData).decode("utf-8")
            print("[INFO] Pi Picture added to json data", flush=True)
        except queue.Empty:
            #print("[INFO] No Pictures Available")
            base64PiImage = ""

        try:
            irCamData = socketDict["infra_red_camera"][1].get_nowait()
            base64IrImage = base64.b64encode(irCamData).decode("utf-8")
            print("[INFO] IR Picture added to json data", flush=True)
        except queue.Empty:
            #print("[INFO] No Pictures Available")
            base64IrImage = ""

        event_Data = eventCameraDict[testSerial].getEventBuffer()
        IMU_Data = socketDict["i_m_u"][2].getDataBuffer()
        if IMU_Data:
            IMU_Data = [data.decode("utf-8") for data in IMU_Data]
        Atmos_Data = socketDict["atmos_temp_sensor"][2].getDataBuffer()
        #print(Atmos_Data)
        if Atmos_Data:
            Atmos_Data = [data.decode("utf-8") for data in Atmos_Data]
        IR_Data = base64IrImage
        PiCam_Data = base64PiImage
        Telem_Data = socketDict["cube_red_telemetry"][2].getDataBuffer()
        if Telem_Data:
            Telem_Data = [data.decode("utf-8") for data in Telem_Data]

        eventideChunk = {
            "Timestamp":time.time(),
            "GPS_data": GPS_data,
            "IMU": IMU_Data,
            "Telem_Data": Telem_Data,
            "Atmos": Atmos_Data,
            "Event_data": event_Data,
            "Picam_data": PiCam_Data,
            "IR_data": IR_Data,
            "Metadata": metadataList
        }

        #print(eventideChunk)
        eventideString = json.dumps(eventideChunk).encode() + b'\n'
        eventideDataHandler.write_data(eventideString)

        try:
            GPS_data = socketDict["g_p_s"][1].get(block=True, timeout=5).decode("utf-8")
        except queue.Empty:
            GPS_data = ""
            print("[INFO] No GPS packets available", flush=True)
        
        
        
        
