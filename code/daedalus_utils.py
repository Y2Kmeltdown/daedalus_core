import os
import subprocess
import time
import serial
from threading import Thread, Lock
import pathlib
import queue
import re
import os
import socket
import sys
import pickle

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

import pyudev
import numpy as np

data_lock = Lock()

IP_ADDR   = "169.254.100.1/16"
IFACE     = "eth0"
def configure_interface(addr: str = IP_ADDR, iface: str = IFACE) -> None:
    """Add a link-local address and bring the interface up if needed."""
    # 1. Need CAP_NET_ADMIN privileges → easiest path: run script with sudo
    if os.geteuid() != 0:
        sys.exit("[ERROR] Please run this script with sudo (needs NET_ADMIN)")

    # 2. Is the address already assigned?
    has_ip = subprocess.run(
        ["ip", "-4", "-o", "addr", "show", "dev", iface],
        capture_output=True, text=True, check=False
    )
    if addr.split("/")[0] in has_ip.stdout:
        print(f"[INFO] {iface} already has {addr}")
    else:
        print(f"[INFO] Adding {addr} to {iface}")
        subprocess.run(
            ["ip", "addr", "add", addr, "dev", iface],
            check=True
        )

    # 3. Make sure the link is up
    subprocess.run(["ip", "link", "set", "dev", iface, "up"], check=True)

class data_handler:
    def __init__(
            self, 
            sensorName:str, 
            extension:str ,
            dataPath:str, 
            backupPath:str, 
            recordingTime:int ,
            pickle:bool = False,
            socketPath:str = None,
            bufferInterval:int = 10,
            socket_check_time:int = 30
            ):
        self.sensorName = sensorName
        self._sensorExtension = extension
        self._usepickle = pickle

        self._dataDirExists = False
        self._backupDirExists = False
        self._socketDirExists = False
        self._dataIsMounted = False
        self._backupIsMounted = False
        self._socketIsMounted = False

        self.index = 0

        self.dataPath = Path(dataPath)
        self.backupPath = Path(backupPath)
        if socketPath:
            self.socketPath = Path(socketPath)
            self.socketQueue = queue.Queue()
            self.socketWrite = Thread(target=self._socketThread, kwargs={"socketQueue":self.socketQueue, "socketPath":str(self.socketPath)}, daemon=True)
            self.socketThreadActive = True
            self.socketWrite.start()
        else:
            self.socketPath = None
        
        self.last_save_time = datetime.now()
        self.last_buffer_save = datetime.now()
        self.socketWriteAnnoucement = datetime.now()
        self.last_socket_check = datetime.now()
        self.buffer_save_interval = timedelta(seconds=bufferInterval)
        self.buffer = []
        self.generate_savepoints()
        self.generate_filename()
        self.record_time = recordingTime
        self.socket_check_time = socket_check_time
        socketCheckThread = Thread(target=self._check_socket, daemon=True)
        socketCheckThread.start()
        if self.record_time > 0:
            print(f"[INFO] {sensorName} Filename Generator Thread Starting", flush=True)
            fileNameThread = Thread(target=self._savepoint_thread, daemon=True)
            fileNameThread.start()
        
    def validate_savepoints(self):

        def validate_directory(directory:Path) -> tuple[bool, bool]:
            if "/mnt" in str(directory):
                drives = self.monitor_usb_drives()
                if drives:
                    for drive in drives:
                        if drive['mount_point'] in str(directory) or drive['fstab_mount'] in str(directory):
                            isMounted = True
                            break
                        isMounted = False
                else:
                    isMounted = False
            else:
                isMounted = True

            if isMounted: # if path is mounted
                pathExists = os.path.exists(directory)
            else:
                pathExists = False

            if ".sock" in str(directory):
                
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.connect(str(directory)) 
                    print("[INFO] Socket connection established. Writing data to socket.", flush=True)
                    pathExists = True
                except:
                    pathExists = False
   
            return isMounted, pathExists
        
        self._dataIsMounted, self._dataDirExists = validate_directory(self.dataPath)
        self._backupIsMounted, self._backupDirExists = validate_directory(self.backupPath)
        if self.socketPath:
            self._socketIsMounted, self._socketDirExists = validate_directory(self.socketPath)
        
    def generate_savepoints(self):

        def generate_directory(directory:Path, isMounted:bool, exists:bool):
            if isMounted and not exists:
                os.makedirs(directory)
            
        self.validate_savepoints()
        generate_directory(self.dataPath, self._dataIsMounted, self._dataDirExists)
        generate_directory(self.backupPath, self._backupIsMounted, self._backupDirExists)
        self.validate_savepoints()
        

    def generate_filename(self):
        print(f"\n[INFO] Creating new file at {datetime.now().strftime('%H:%M:%S')}", flush=True)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.index += 1
        self.file_name = f"{self.sensorName}_data_{current_time}_{self.index}{self._sensorExtension}"

    def _savepoint_thread(self):
        while True:
            if (datetime.now() - self.last_save_time).total_seconds() >= self.record_time:
                if not self._socketDirExists:
                    self.last_save_time = datetime.now()
                    self.generate_filename()
                    self.validate_savepoints()
            time.sleep(1)

    def _check_socket(self):
        while True:
            if (datetime.now() - self.last_socket_check).total_seconds() >= self.socket_check_time:
                if not self._socketDirExists:
                    self.last_socket_check = datetime.now()
                    self.validate_savepoints()
        

    def getRTC():
        kernelTime = os.popen(f"sudo hwclock -r").read()
        return kernelTime
        
    def write_data(self, data, now:bool = False, flush:bool = False):
        if data:
            if self._usepickle:
                pass
            elif isinstance(data, list):
                if isinstance(data[0], bytes):
                    data = b"".join(data)
                elif isinstance(data[0], str):
                    data = "".join(data)
                else:
                    raise TypeError("Data within a list must be string or bytes")
            

            if self._usepickle:
                pass
            elif isinstance(data, str):
                data = data.encode('utf-8')
            elif not isinstance(data, bytes):
                raise TypeError("Data must be string or bytes")
            
            if self._socketDirExists:
                if datetime.now() >= self.socketWriteAnnoucement + self.buffer_save_interval:
                    print(f"[INFO] Socket Valid at {datetime.now().strftime('%H:%M:%S')}...", flush=True)
                    self.socketWriteAnnoucement = datetime.now()
                self.socketQueue.put(data)
            else:
                if not self._dataDirExists and not self._backupDirExists:
                    raise IOError("No valid locations exist to write data")
                
                self.buffer.append(data)
                #print(self.buffer)
                #print(self.buffer)
                if datetime.now() - self.last_buffer_save >= self.buffer_save_interval and self.buffer or now == True or flush == True:
                    if now:
                        self.generate_filename()
                    print(f"[INFO] Writing Buffer at {datetime.now().strftime('%H:%M:%S')}...", flush=True)
                    
                    if self._usepickle and flush:
                        writeData = data
                    elif self._usepickle:
                        writeData = self.buffer
                    else:
                        writeData = b"".join(self.buffer)

                    if self._dataDirExists:
                        dataFile = self.dataPath / self.file_name
                        dataWrite = Thread(target=self._writerThread, kwargs={"data":writeData, "path":dataFile}, daemon=True)
                        dataWrite.start()

                    if self._backupDirExists:
                        backupFile = self.backupPath / self.file_name
                        backupWrite = Thread(target=self._writerThread, kwargs={"data":writeData, "path":backupFile}, daemon=True)
                        backupWrite.start()

                    self.buffer.clear()  # Clear buffer after writing
                    self.last_buffer_save = datetime.now()

                    if self._dataDirExists:
                        dataWrite.join()
                    
                    if self._backupDirExists:
                        backupWrite.join()
        else:
            pass
            #print("[INFO] No Data provided at the time of writing data.")

    # def pickle_append(filename, obj):
    #     with open(filename, 'ab+') as f:
    #         pickle.dump(obj, f)
    #         f.flush()

    # def pickle_load(filename):
    #     with open(filename, 'rb') as f:
    #         while True:
    #             try:
    #                 yield pickle.load(f)
    #             except EOFError:
    #                 break

    def _writerThread(self, data, path):
        try:
            if self._usepickle:
                with open(path, "a+b") as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with open(path, "ab+") as f:
                    f.write(data)
                    f.flush()
        except Exception as e:
            print(f"[WARNING] Failed to write to file: {path}\n {e}")
            self.validate_savepoints()

    def _socketThread(self, socketQueue:queue.Queue, socketPath):
        while True:
            if self._socketDirExists:
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.connect(socketPath)
                        while True:
                            data = socketQueue.get()
                            s.sendall(data)
                            EOTString = f"EOT{chr(3)}{chr(4)}".encode("utf-8")
                            s.send(EOTString)   
                except Exception as e:
                    print(f"[WARNING] Failed to write to socket: {socketPath}\n {e}")
                    self.socketThreadActive = False
                    self.validate_savepoints()
            time.sleep(1)

    def monitor_usb_drives(self) -> List[Dict[str, str]]:
        """
        Monitor and detect USB flash drives connected to the system.
        
        Returns:
            List[Dict[str, str]]: List of dictionaries containing information about connected USB drives
        """
        context = pyudev.Context()
        connected_drives = []
        
        try:
            # Find all block devices that are USB storage devices
            for device in context.list_devices(subsystem='block', ID_BUS='usb'):
                # Check if it's a partition (real storage device)
                if device.get('DEVTYPE') == 'partition':
                    # Get both current mounts and fstab configurations
                    mount_info = self.get_mount_point(device.device_node)
                    drive_info = {
                        'device_node': device.device_node,
                        'vendor': device.get('ID_VENDOR', 'Unknown'),
                        'product': device.get('ID_MODEL', 'Unknown'),
                        'mount_point': mount_info['current_mount'],
                        'fstab_mount': mount_info['fstab_mount'],
                        'mount_type': mount_info['mount_type']
                    }
                    connected_drives.append(drive_info)
                    
            return connected_drives
        
        except Exception as e:
            print(f"Error monitoring USB drives: {str(e)}")
            return []

    def get_mount_point(self, device_node: str) -> Dict[str, str]:
        """
        Get comprehensive mounting information for a device.
        
        Args:
            device_node (str): Device node path (e.g., /dev/sda1)
            
        Returns:
            Dict[str, str]: Dictionary containing current_mount, fstab_mount, and mount_type
        """
        mount_info = {
            'current_mount': 'Not Mounted',
            'fstab_mount': 'Not in fstab',
            'mount_type': 'none'
        }
        
        # Check current mounts
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    if device_node in line:
                        mount_info['current_mount'] = line.split()[1]
                        mount_info['mount_type'] = 'active'
        except Exception as e:
            print(f"Error reading current mounts: {str(e)}")
        
        # Check systemd automount points
        try:
            result = subprocess.run(['systemctl', 'list-units', '--type=automount', '--all'],
                                capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if mount_info['current_mount'] in line:
                    mount_info['mount_type'] = 'automount'
        except Exception as e:
            print(f"Error checking systemd automounts: {str(e)}")
        
        # Check fstab entries
        try:
            with open('/etc/fstab', 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    if device_node in line:
                        fields = line.split()
                        mount_info['fstab_mount'] = fields[1]
                        if 'x-systemd.automount' in line:
                            mount_info['mount_type'] = 'automount'
        except Exception as e:
            print(f"Error reading fstab: {str(e)}")
        
        return mount_info

class supervisor:
    def __init__(self, supervisorFile:str):
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

            supervisorDict[programDict["program"]] = self.supervisorModule(programDict)

        self.moduleDict = supervisorDict
    class supervisorModule:
        sizeDelta = 0
        displayed = False


        def __init__(self, programDict:dict):
            self.name = programDict["program"]

            self.shorthand = "".join(re.findall(r'(?:^|_)(\w)', self.name))

            # Get Main Save Location
            location = re.search(r'(?<=--data\s)[^\s]+', programDict["command"])
            if location is not None:
                self.location = Path(location.group())
                self.folderSize = self._getFolderSize(self.location)
            else:
                self.location = None

            # Get Socket Location
            sock = re.search(r'(?<=--socket\s)[^\s]+', programDict["command"])
            if sock is not None:
                self.sock = Path(sock.group())
            else:
                self.sock = None
            
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
            circle = "O"
            cross = "X"
            status = self.getStatus()
            if status:
                statusString = circle
            else:
                statusString = cross

            shorthandfmtd = "{: <4}".format(f"{self.shorthand}")
            
            sizeDelta = self.getSizeDelta()

            sizeString = self._get_appropriate_byte(sizeDelta)

            return "{: <21}".format(f"{statusString} | {shorthandfmtd} | {sizeString}")
    
class transceiver:
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
        self._serial_lock = Lock()
        self._initialise_transceiver()
        self._stats = {
            'messages_received': 0,
            'bytes_received': 0,
            'invalid_messages': 0,
            'parse_errors': 0
        }

    def _initialise_transceiver(self):
        # Create separate threads for transmit and receive
        transmitThread = Thread(target=self._transmitter, daemon=True)
        receiveThread = Thread(target=self._receiver, daemon=True)
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
            return bytearray()

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
                    elif data != b"":
                        socketBuffer.append(data)
                        #print(data[-5:])
                    elif data == b"":
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