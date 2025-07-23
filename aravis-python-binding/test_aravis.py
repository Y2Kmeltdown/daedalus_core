import aravis
from PIL import Image
from queue import LifoQueue
import time
from threading import Thread
import subprocess
import sys
import os

width = 640
height = 480
testQueue = LifoQueue(maxsize=100)

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


def queueRetriever(testQueue:LifoQueue):
    try:
        while True:
            data = testQueue.get()
    except:
        pass

try:
    configure_interface(addr=IP_ADDR, iface=IFACE)
    # buffer = aravis.get_camera_buffer()
    # print(buffer)
    # img = Image.frombytes('L', (width, height), bytes(buffer))
    # img = img.save(f"data/test.jpg")
    
    # buffers = aravis.get_camera_buffers(60)
    # for i, buffer in enumerate(buffers):
    #     print(len(buffer))
    #     img = Image.frombytes('L', (width, height), bytes(buffer))
    #     img = img.save(f"data/test{i}.jpg")
    testThread = Thread(target=queueRetriever, args=(testQueue, ), daemon=True)
    testThread.start()
    i = 0
    frameStart = time.monotonic_ns()
    totalStart = time.monotonic_ns()
    computeTime = ""
    for buf in aravis.ir_buffer_streamer():
        frameNo = f"Frame: {i-1}"
        totalEnd = time.monotonic_ns()
        totalTime = f"Total Time:{totalEnd-totalStart}"
        totalStart = time.monotonic_ns()
        frameEnd = time.monotonic_ns()
        frameTime = f"Frame Timing:{frameEnd-frameStart}"
        print(f"{frameNo}\n{frameTime}\n{computeTime}\n{totalTime}\n")
        computeStart = time.monotonic_ns()
        i += 1
        if buf:
            img = Image.frombytes('L', (width, height), bytes(buf))
            if testQueue.full():
                testQueue.queue.clear()
            testQueue.put_nowait(img)
        
        # if i % 2:
        #     time.sleep(0.001)
            
        computeEnd = time.monotonic_ns()
        computeTime = f"Compute Time:{computeEnd-computeStart}"
        
        frameStart = time.monotonic_ns()

except Exception as e:
    print(f"Error: {e}") 