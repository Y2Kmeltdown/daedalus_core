import socket
from threading import Thread
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



def socketServer(socketFile:str, socketQueue:queue.Queue):
    if os.path.exists(socketFile):
        os.remove(socketFile)  

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socketFile)
    while True:
        server.listen(1)
        conn, addr = server.accept()
        data = conn.recv(1024)
        print(data)
        if data is not None:
            socketQueue.put(data)


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

    supervisorFile = "../config/supervisord.conf"
    eventide = daedalus_utils.supervisor(supervisorFile)

    eventideDataHandler = daedalus_utils.data_handler(
        sensorName=f"event_synced",
        extension=".json",
        dataPath=args.data,
        backupPath=args.backup
        )
    

    # Socket Handler
    socketList = []
    for supervisorObject in eventide.moduleDict.values():
        sock = supervisorObject.sock
        if sock is not None:
            socketList.append(sock)

    print(socketList)

    socketThreads = []
    socketQueues = []
    for sock in socketList:
        socketQueue = queue.Queue()
        socketFile = str(sock)
        socketThread = Thread(target=socketServer, kwargs={"socketFile":socketFile, "socketQueue":socketQueue}, daemon=True)
        socketThread.start()
        socketThreads.append(socketThread)
        socketQueues.append(socketQueue)

    while(True):
        pass
    

