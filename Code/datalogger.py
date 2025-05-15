import socket
from threading import Thread




sock = "/tmp/socket_test.s"

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect(sock)
    data = s.recv(1024)

# Set up client to read data from multiple servers possible independent threads based on sockets found
# Open File on USB and SD Card
# organise data collection based on GPS packets
# Save Data and repeat