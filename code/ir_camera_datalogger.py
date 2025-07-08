#!/usr/bin/env python3
import time
import datetime
import argparse
import sys
import io
import os
import subprocess

from PIL import Image
import aravis
import daedalus_utils
import shlex


W, H = 640, 480
PAYLOAD = W * H


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
    
def ir_frame_logger(data_handler, timer: float):
    """
    Pulls frames from aravis.ir_buffer_streamer(), wraps them as PNGs
    """
    for idx, buf in enumerate(aravis.ir_buffer_streamer()):
        raw = bytes(buf)
        ln  = len(raw)

        if ln < PAYLOAD:
            print(f"[!] frame {idx} too small ({ln} bytes), skipping")
            continue
  
        if ln > PAYLOAD:
            raw = raw[:PAYLOAD]

        img = Image.frombuffer('L', (W, H), raw, 'raw', 'L', 0, 1)
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)

        chunk_size = 4096
        bytes_list = []
        while True:
            chunk = bio.read(chunk_size)
            if not chunk:
                break
            bytes_list.append(chunk)

        data_handler.write_data(bytes_list, now=True)
        time.sleep(timer)

if __name__ == "__main__":
    configure_interface()
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--data",
        default="/usr/local/daedalus/data/ir_data",
        help="Root directory where recordings are stored",
    )
    parser.add_argument(
        "--backup",
        default="/mnt/data/ir_data",
        help="Root directory where backups are written",
    )
    parser.add_argument(
        "--timer",
        default=1.0,
        type=float,
        help="Seconds between consecutive snapshots",
    )
    parser.add_argument(
        "--socket",
        default="/tmp/irImage.sock",
        help="Unix socket path for signalling (if used)",
    )
    args = parser.parse_args()

    # data_path   = os.path.join(args.data,   "ir_frames")
    # backup_path = os.path.join(args.backup, "ir_frames")

    irDataHandler = daedalus_utils.data_handler(
        sensorName="ir_frames",
        extension=".png",
        dataPath=args.data,
        backupPath=args.backup,
        recordingTime=0,
        socketPath=args.socket
    )

    try:
        print(f"[INFO] Starting IR frame logger")
        ir_frame_logger(irDataHandler, args.timer)

    except (KeyboardInterrupt, SystemExit):
        print("\n[INFO] Stopping IR frame logger")
        sys.exit(0)
