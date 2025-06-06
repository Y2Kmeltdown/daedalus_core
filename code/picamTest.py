from picamera2 import Picamera2
import io
import time
picam2 = Picamera2()
picam2.start()
time.sleep(1)
data = io.BytesIO()
picam2.capture_file(data, format='png')
data.seek(0)  # Ensure you're at the beginning of the BytesIO object
chunk_size = 4096  # Define a suitable chunk size

while True:
    chunk = data.read(chunk_size)
    if not chunk:
        break  # End of data
    


