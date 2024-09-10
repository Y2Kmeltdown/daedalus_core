#!/usr/bin/python
'''
  A Simple mjpg stream http server for the Raspberry Pi Camera
  inspired by https://gist.github.com/n3wtron/4624820
'''

from http.server import BaseHTTPRequestHandler,HTTPServer
import io
import time
from picamera2 import Picamera2
import argparse

camera=None


class CamHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    if self.path.endswith('.mjpg'):
      self.send_response(200)
      self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
      self.end_headers()
      stream=io.BytesIO()
      try:
        start=time.time()
        for foo in camera.capture_continuous(stream,'jpeg', use_video_port=True):
          self.wfile.write(bytes("--jpgboundary", "utf8"))
          self.send_header('Content-type','image/jpeg')
          self.send_header('Content-length',len(stream.getvalue()))
          self.end_headers()
          self.wfile.write(stream.getvalue())
          stream.seek(0)
          stream.truncate()
          #time.sleep(.5)
      except KeyboardInterrupt:
        pass
      return
    else:
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      self.wfile.write(bytes("<html><head></head><body><img src='/cam.mjpg'/></body></html>", "utf8"))
      return

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("camera", help="Camera number (for example 0 or 1)")
parser.add_argument(
    "--port",
    default=8080,
    type=int,
    help="Port at which server is available on"
)
args = parser.parse_args()

def main():
  global camera
  camera = Picamera2(int(args.camera))
  camera.resolution = (1280, 960)
  #camera.resolution = (640, 480)
  global img
  try:
    server = HTTPServer(('',args.port),CamHandler)
    print("server started")
    server.serve_forever()
  except KeyboardInterrupt:
    camera.close()
    server.socket.close()

if __name__ == '__main__':
  main()