# import aravis
# from PIL import Image

# W, H = 640, 480
# PAYLOAD = W * H

# for idx, buf in enumerate(aravis.ir_buffer_streamer()):
#     raw = bytes(buf)               # grab the buffer’s bytes
#     ln  = len(raw)

#     # if it’s too small, skip
#     if ln < PAYLOAD:
#         print(f"[!] frame {idx} too small ({ln} < {PAYLOAD}), skipping")
#         continue
#     # if it’s larger (e.g. header+payload), take just the first PAYLOAD bytes
#     if ln > PAYLOAD:
#         raw = raw[:PAYLOAD]

#     # build and save the L-mode image
#     img = Image.frombuffer('L', (W, H), raw, 'raw', 'L', 0, 1)
#     img.save(f"../frame_{idx:04d}.png")
#     print(f"Frame {idx} saved")

#!/usr/bin/env python3
import time
import datetime
import argparse
import sys
import io
import os

from PIL import Image
import aravis
import daedalus_utils

W, H = 640, 480
PAYLOAD = W * H

def ir_frame_logger(data_handler, timer: float):
    """
    Pulls frames from aravis.ir_buffer_streamer(), wraps them as PNGs,
    and hands them off to data_handler.write_data(...).
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
        default=5.0,
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
