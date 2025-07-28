import serial
from pymavlink import mavutil
import threading
import logging
import os


logging.basicConfig()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("server")
log_level = getattr(logging, log_level)
logger.setLevel(log_level)

port = "COM14"
baud = 115200

#ser = serial.Serial(port, baud)
connection = mavutil.mavlink_connection('COM14', baud=115200)  # or 'udp:127.0.0.1:14550'

# Wait for a heartbeat to ensure connection
connection.wait_heartbeat()


def send_gimbal_command(conn:mavutil, messageID:int):
    conn.mav.command_long_send(
    conn.target_system,
    mavutil.mavlink.MAV_COMP_ID_PERIPHERAL,
    mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
    0,
    messageID,
    0,
    0,
    0,
    0,
    0,
    1,
    )

def _watch_telem(conn:mavutil):
    try:
        i = 0
        while True:
            i+=1
            msg = conn.recv_match(blocking=True)
            if msg:
                print(msg)

            if i == 50:
                break


    except KeyboardInterrupt:
        logger.warning("Keyboard Interrupt, exiting...")

messageWatcher = threading.Thread(target=_watch_telem, args=(connection,), daemon=True)

try:
    messageWatcher.start()
    for i in list(range(5)):
        
        send_gimbal_command(conn=connection, messageID=i)
except KeyboardInterrupt:
    logger.warning("Keyboard Interrupt, exiting...")
finally:
    
    messageWatcher.join()