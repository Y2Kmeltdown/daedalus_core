import time
import serial
import threading
import queue

from pathlib import Path
import numpy as np
import os
import re
import argparse

import glob
import os



class supervisorObject:
    sizeDelta = 0
    displayed = False


    def __init__(self, programDict:dict):
        self.name = programDict["program"]
        self.shorthand = "".join(re.findall(r'(?:^|_)(\w)', self.name))
        locationTest = re.search(r'(?<=--data\s)[^\s]+', programDict["command"])
        if locationTest is not None:
            self.location = Path(locationTest.group())
            self.folderSize = self._getFolderSize(self.location)
        else:
            self.location = None
        self.updateTime = time.monotonic_ns()
        self._objectInformation = programDict
        self.getStatus()

    def _getFolderSize(self, folder:Path):
        return sum(f.stat().st_size for f in folder.glob('**/*') if f.is_file())
    
    # Function to determine the appropriate units for folder size
    def _get_appropriate_byte(self, fsize):
        for funit in ['B', 'kB', 'MB', 'GB']:
            if len(str(fsize)) > 4:
                fsize = np.round(fsize/1024, decimals=1)
                continue
                
            fsize_str = f'{fsize} {funit}/s'
            return fsize_str

    def getStatus(self):
        #re.findall(r'[\w:]+', text)
        try:
            statusData = os.popen(f"sudo supervisorctl status {self.name}").read()
            if "RUNNING" in statusData:
                self.status = True
            elif "STARTING" in statusData:
                self.status = False
            elif "BACKOFF" in statusData:
                self.status = False
            elif "STOPPED" in statusData:
                self.status = False
            else:
                self.status = False
        except:
            self.status = False

        return self.status
    
    def getSizeDelta(self):
        oldFolderSize = self.folderSize
        oldTime = self.updateTime
        currentFolderSize = self._getFolderSize(self.location)
        currentTime = time.monotonic_ns()
        sizeDelta = ((currentFolderSize-oldFolderSize)/((currentTime-oldTime)/1000000000))
        self.sizeDelta=sizeDelta
        self.folderSize = currentFolderSize
        self.updateTime = currentTime
        return sizeDelta

    def generateProgramString(self):
        status = self.getStatus()
        if status:
            statusString = circle
        else:
            statusString = cross

        shorthandfmtd = "{: <4}".format(f"{self.shorthand}")
        
        sizeDelta = self.getSizeDelta()

        sizeString = self._get_appropriate_byte(sizeDelta)

        return "{: <21}".format(f"{statusString} | {shorthandfmtd} | {sizeString}")

class transceiverObject:
    MAX_QUEUE_SIZE = 1000  # Maximum number of messages to queue
    _receiveQueue = queue.Queue()
    _transmitQueue = queue.Queue()
    def __init__(self, port, baudrate):
        self._port = port
        self._baudrate = baudrate
        self._serial = serial.Serial(
            self._port, 
            self._baudrate, 
            timeout=0,
            xonxoff=False,     # disable software flow control
            rtscts=False,      # disable hardware flow control
            dsrdtr=False,       # disable hardware flow control
            writeTimeout=0
        )
        self._serial_lock = threading.Lock()
        self._initialise_transceiver()
        self._stats = {
            'messages_received': 0,
            'bytes_received': 0,
            'invalid_messages': 0,
            'parse_errors': 0
        }

    def _initialise_transceiver(self):
        # Create separate threads for transmit and receive
        transmitThread = threading.Thread(target=self._transmitter, daemon=True)
        receiveThread = threading.Thread(target=self._receiver, daemon=True)
        transmitThread.start()
        receiveThread.start()
        
    def _transmitter(self):
        while True:
            try:
                # Process all pending messages in queue
                while not self._transmitQueue.empty():
                    data = self._transmitQueue.get()
                    #print(f"Attempting to transmit: {data}")
                    with self._serial_lock:
                        bytes_written = self._serial.write(data)
                        self._serial.flush()
                        if bytes_written != len(data):
                            print(f"Warning: Only {bytes_written}/{len(data)} bytes written")
                    #print(f"Transmitted: {data}")
                    
                    # Mark task as done
                    self._transmitQueue.task_done()
                    
            except serial.SerialException as e:
                print(f"Serial error during transmission: {e}")
            except Exception as e:
                print(f"Unexpected error during transmission: {e}")
                
            # Small sleep to prevent CPU thrashing
            time.sleep(0.001)

    def _receiver(self):
        buffer = bytearray()
        while True:
            try:
                with self._serial_lock:
                    if self._serial.in_waiting:
                        packet = self._serial.read(self._serial.in_waiting)
                        #print(f"Received: {packet}")
                        if packet:
                            buffer.extend(packet)
                            
                            # Process complete messages (handling both \n and \r)
                            while True:
                                # Look for either delimiter
                                n_pos = buffer.find(b'\n')
                                r_pos = buffer.find(b'\r')
                                
                                # No delimiters found
                                if n_pos == -1 and r_pos == -1:
                                    break
                                    
                                # Find the first occurring delimiter
                                if n_pos == -1:
                                    split_pos = r_pos
                                elif r_pos == -1:
                                    split_pos = n_pos
                                else:
                                    split_pos = min(n_pos, r_pos)
                                
                                # Split at delimiter
                                message = buffer[:split_pos]
                                buffer = buffer[split_pos + 1:]
                                
                                # Skip any additional adjacent delimiters
                                while buffer and buffer[0] in b'\r\n':
                                    buffer = buffer[1:]
                                    
                                if message:  # Ignore empty messages
                                    self._handle_received_data(message)
                                    
            except serial.SerialException as e:
                print(f"Serial error during reception: {e}")
            except Exception as e:
                print(f"Unexpected error during reception: {e}")
                
            time.sleep(0.001)

    def receive(self):
        try:
            # Use get_nowait() instead of get() to prevent blocking
            data = self._receiveQueue.get_nowait()
            self._receiveQueue.task_done()
            return data
        except queue.Empty:
            return None

    def transmit(self, data):
        # Add type checking and encoding handling
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif not isinstance(data, bytes):
            raise TypeError("Data must be string or bytes")
        
        self._transmitQueue.put(data)
                
    def _parse_message(self, data):
        """Parse received message according to protocol"""
        try:
            # Example: Parse JSON
            # return json.loads(data.decode('utf-8'))
            return data
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None

    def _handle_received_data(self, data):
        """Process received data before queuing"""
        try:
            # Optional: Decode if needed
            # decoded_data = data.decode('utf-8')
            
            # Check queue size before adding
            if self._receiveQueue.qsize() > self.MAX_QUEUE_SIZE:
                print("Warning: Receive queue full, dropping oldest message")
                try:
                    self._receiveQueue.get_nowait()  # Remove oldest message
                    self._receiveQueue.task_done()
                except queue.Empty:
                    pass
            
            self._receiveQueue.put(data)
            
        except UnicodeDecodeError as e:
            print(f"Error decoding received data: {e}")
        except Exception as e:
            print(f"Error processing received data: {e}")

    def get_receive_queue_size(self):
        """Return current size of receive queue"""
        return self._receiveQueue.qsize()

    def flush_receive_queue(self):
        """Clear all pending received messages"""
        while not self._receiveQueue.empty():
            try:
                self._receiveQueue.get_nowait()
                self._receiveQueue.task_done()
            except queue.Empty:
                break

    def wait_for_data(self, timeout=1.0):
        """Wait for data with timeout"""
        try:
            data = self._receiveQueue.get(timeout=timeout)
            self._receiveQueue.task_done()
            return data
        except queue.Empty:
            return None

def generateSupervisorObjects(supervisorFile:str):
    with open(supervisorFile, "r") as config:
        configString = "".join(config.readlines())

    programs = re.findall(r'\[program:[\s\S]*?\r?\n\r?\n', configString)
    supervisorDict = {}
    for program in programs:
        programDict = {}
        programLines = program.split("\n")
        for num, line in enumerate(programLines):
            if num == 0:
                programDict["program"] = re.search(r'(?<=\[program:)[^\]]+(?=\])', programLines[0]).group()
            elif line != "":
                splitLines = line.split("=")
                programDict[splitLines[0]]=splitLines[1]

        supervisorDict[programDict["program"]] = supervisorObject(programDict)

    return supervisorDict

def generateDataString(gpsObject:supervisorObject, eventObject:supervisorObject):
    eventBytes = eventObject.getSizeDelta()
    list_of_files = glob.glob(str(gpsObject.location)+"/*") # * means all if need specific format then *.csv
    lastGPSFile = max(list_of_files, key=os.path.getctime)
    with open(lastGPSFile) as f:
        recentGPSData = "".join(f.readlines()[-50:-1])
    recentCoords = re.findall(r'^\$GNRMC.*', recentGPSData, re.M)[-1]
    output = f"{eventBytes}\r\n{recentCoords}\r\n".encode("utf-8")

    return output
        
        


if __name__ == '__main__':
    #parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    #parser.add_argument("port", help="Serial Port for GPS", type=str)
    #args = parser.parse_args()
    port = "COM8"
    baudrate = "57600"
    supervisorFile = "../config/supervisord.conf"
    transceiver = transceiverObject(port, baudrate)


    print("Daedalus RF Transmitter\n")
    
    time.sleep(1)
    
    supervisorDict = generateSupervisorObjects(supervisorFile)

    while True:
        dataString = generateDataString(supervisorDict["g_p_s"], supervisorDict["event_based_camera"])
        transceiver.transmit(dataString)
        time.sleep(2)
