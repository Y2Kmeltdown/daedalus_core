import socket
from threading import Thread, Lock
import daedalus_utils
import argparse
import time
import json
import datetime
import pathlib
import queue
import os


import socket, time
from threading import Thread

eventList = []


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
            data = conn.recv(20000)
    
            if data is not None:
                self.socketQueue.put(data)
                self.socketQueue.task_done()



# Set up client to read data from multiple servers possible independent threads based on sockets found
# Open File on USB and SD Card
# organise data collection based on GPS packets
# Save Data and repeat

# Step 1 generate daedalus object and pull sockets from them and create the sockets
# Step 2 generate independent threads for each socket identified with a queue or pipe to the main loop
# Step 3 set up a data structure for saving the data based on GPS packets and unix timestamps
# Step 4 
# This will handle all of the socket servers for the system based on the sock files it finds in supervisor with special exceptions for event data and GPS data
# It will start the socket servers in independent threads and then pool the data then group it based on GPS packets and timestamps for all data it receives
# The data will be in JSON format with the header for each subsection the GPS packet that relates to the specific data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
        "--record_time",
        default=300,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()

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

    # Handle special cases E.G. pi camera, GPS
    # Handle unix timestamping
    # Handle JSON or dictionary placement

    

    while(True):
        pass

            
            
    

