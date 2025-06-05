import socket

HOST = "/tmp/socket_test.s"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect(HOST)
    s.sendall(b"Hello, world")
    data = s.recv(1024)

print(f"Received {data!r}")
