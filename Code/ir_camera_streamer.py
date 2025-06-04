#!/usr/bin/env python3

import os
import io
import time
import logging
import socketserver
from http import server
from threading import Condition, Thread
import argparse
import glob
import subprocess
from PIL import Image

# Streamed HTML Page
PAGE = """\
<html>
<head>
<title>IR MJPEG Streaming</title>
</head>
<body>
<h1>Live IR MJPEG Stream</h1>
<img src="stream.mjpg" width="640" height="480" />
</body>
</html>
"""

class StreamingOutput:
    def __init__(self, frame_dir):
        self.condition = Condition()
        self.frame = None
        self.frame_dir = frame_dir
        self.running = True

    def start(self):
        def run():
            while self.running:
                frames = sorted(glob.glob(os.path.join(self.frame_dir, "*.pgm")))
                for frame_path in frames:
                    try:
                        with Image.open(frame_path) as img:
                            buf = io.BytesIO()
                            img.save(buf, format="JPEG")
                            with self.condition:
                                self.frame = buf.getvalue()
                                self.condition.notify_all()
                        os.remove(frame_path)
                    except Exception as e:
                        logging.warning(f"Error processing {frame_path}: {e}")
                time.sleep(0.01)
        Thread(target=run, daemon=True).start()

    def stop(self):
        self.running = False


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(f"Client disconnected: {e}")
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8002, help='Port to serve the stream')
    parser.add_argument('--frame_dir', default='/home/daedalus/daedalus_core/aravis-c-examples/build/out_frames', help='Directory with .pgm frames')
    parser.add_argument('--cmd', default='/home/daedalus/daedalus_core/aravis-c-examples/build/06-multi-save -o /home/daedalus/daedalus_core/aravis-c-examples/build/out_frames -f 5',
                        help='Command to capture IR frames')
    args = parser.parse_args()

    # Clean frame directory
    os.makedirs(args.frame_dir, exist_ok=True)
    for f in glob.glob(os.path.join(args.frame_dir, '*.pgm')):
        os.remove(f)

    # Start frame capture process
    subprocess.Popen(args.cmd, shell=True)

    # Start streamer
    output = StreamingOutput(args.frame_dir)
    output.start()

    print(f"Serving MJPEG stream on port {args.port}...")
    try:
        server = StreamingServer(('', args.port), StreamingHandler)
        server.serve_forever()
    finally:
        output.stop()
