import socket
from threading import Thread
import daedalus_utils
import argparse
import time
import json
import datetime
import pathlib




sock = "/tmp/socket_test.s"

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect(sock)
    data = s.recv(1024)

# Set up client to read data from multiple servers possible independent threads based on sockets found
# Open File on USB and SD Card
# organise data collection based on GPS packets
# Save Data and repeat

# This will handle all of the socket servers for the system based on the sock files it finds in supervisor with special exceptions for event data and GPS data
# It will start the socket servers in independent threads and then pool the data then group it based on GPS packets and timestamps for all data it receives
# The data will be in JSON format with the header for each subsection the GPS packet that relates to the specific data

if __name__ == "__main__":
    pass

