# -*- coding: utf-8 -*-
import socket
import os, os.path

sock = "/tmp/socket_test.s"
if os.path.exists(sock):
  os.remove(sock)    

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(sock)
while True:
  server.listen(1)
  conn, addr = server.accept()
  data = "1"
  conn.sendall(data)
  