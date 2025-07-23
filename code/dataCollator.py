import qwiic_oled_display
import daedalus_utils
import argparse
import queue
import base64
import time
import sys
import numpy as np
import json

def run_display(display_string, myOLED):

    if myOLED.is_connected() == False:
        print("The Qwiic OLED Display isn't connected to the system. Please check your connection", \
            file=sys.stderr)
        return
    
    myOLED.begin()
    # ~ myOLED.clear(myOLED.ALL)
    myOLED.clear(myOLED.PAGE)  #  Clear the display's buffer
    myOLED.print(display_string)
    print(display_string, flush=True)
    myOLED.display()

def socketGenerator(supervisor:daedalus_utils.supervisor):
    # Socket Handler
    socketDict = {}
    for key, supervisorObject in supervisor.moduleDict.items():
        sock = supervisorObject.sock
        if sock is not None:
            socketQueue = queue.Queue()
            socketFile = str(sock)
            if key == "g_p_s":# or key == "pi_picture_camera":
                buffer = False
            elif key == "pi_picture_camera":
                buffer = False
            elif key == "infra_red_camera":
                buffer = False
            if key == "event_based_camera":
                buffer = True
                bufsize = 32768
            else:
                buffer = True
                bufsize = 4096
            socketThread = daedalus_utils.socketServer(key, socketFile=socketFile, socketQueue=socketQueue, buffer=buffer, bufsize=bufsize)
            socketThread.start()
            socketDict[key] = (socketFile, socketQueue, socketThread)
    return socketDict

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--data",
        default="/home/daedalus/daedalus_core/data",
        help="Path of the directory where recordings are stored",
    )
    parser.add_argument(
        "--backup",
        default=str("/mnt/data"),
        help="Path of the directory where recordings are backed up",
    )
    parser.add_argument(
        "--record_time",
        default=300,
        type=int,
        help="Time in seconds for how long to record to a single file"
    )
    args = parser.parse_args()

    # INITIAL SUPERVISOR ACCESS AND DATA HANDLER
    supervisorFile = "config/supervisord.conf"
    daedalus = daedalus_utils.supervisor(supervisorFile)
    daedalusDataHandler = daedalus_utils.data_handler(
        sensorName=f"event_synced",
        extension=".pickle",
        dataPath=args.data,
        backupPath=args.backup,
        recordingTime=args.record_time,
        pickle=True
        )
    
    socketDict = socketGenerator(daedalus)

    # # Initialise display
    # #tick = "✓"
    # #cross = "✗"
    # supervisorFile = "../config/supervisord.conf"
    # pageSize = 4
    # print("Daedalus OLED Display\n")
    # myOLED = qwiic_oled_display.QwiicOledDisplay()
    # time.sleep(1)
    # myOLED.begin()
    # run_display("Daedalus OLED Display initialising...", myOLED)

    # daedalus = daedalus_utils.supervisor(supervisorFile)

    # numberOfPages = len(daedalus.moduleDict)//pageSize
    
    # #TODO Update this to always show event camera on 1st row
    # while True:
    #     for page in range(numberOfPages): # Loop through 4 times to generate data for each row in the page
    #         pageUsage = 0
    #         programStrings = []
    #         for supervisorObject in daedalus.moduleDict.values():
    #             if pageUsage < pageSize:
    #                 if supervisorObject.location is not None and supervisorObject.displayed == False:
    #                     programStrings.append(supervisorObject.generateProgramString())
    #                     pageUsage+=1
    #                     supervisorObject.displayed = True
    #             else:
    #                 break
    #         if programStrings:   
    #             oled_string = "".join(programStrings)
    #             run_display(oled_string, myOLED)
    #             time.sleep(3)
    #     for supervisorObject in daedalus.moduleDict.values():
    #         supervisorObject.displayed = False

    # RUN CODE
    GPS_data = ""
    while True:
        prev_GPS_data = GPS_data

        try:
            piPicData = socketDict["pi_picture_camera"][1].get_nowait()
            print("[INFO] Pi Picture added to json data", flush=True)
        except queue.Empty:
            #print("[INFO] No Pictures Available")
            piPicData = None
        PiCam_Data = piPicData

        try:
            irCamData = socketDict["infra_red_camera"][1].get_nowait()
            print("[INFO] IR Picture added to json data", flush=True)
        except queue.Empty:
            #print("[INFO] No Pictures Available")
            irCamData = None
        IR_Data = irCamData

        event_Data = socketDict["event_based_camera"][2].getDataBuffer()
            
        IMU_Data = socketDict["i_m_u"][2].getDataBuffer()
        if IMU_Data:
            IMU_Data = [data.decode("utf-8") for data in IMU_Data]

        Atmos_Data = socketDict["atmos_temp_sensor"][2].getDataBuffer()
        if Atmos_Data:
            Atmos_Data = [data.decode("utf-8") for data in Atmos_Data]
        
        Telem_Data = socketDict["cube_red_telemetry"][2].getDataBuffer()
        if Telem_Data:
            Telem_Data = [data.decode("utf-8") for data in Telem_Data]

        try:
            GPS_data = socketDict["g_p_s"][1].get(block=True, timeout=5).decode("utf-8")
        except queue.Empty:
            GPS_data = ""
            print("[INFO] No GPS packets available", flush=True)

        daedalusChunk = {
            "Timestamp":time.time(),
            "GPS_data": prev_GPS_data,
            "IMU": IMU_Data,
            "Telem_Data": Telem_Data,
            "Atmos": Atmos_Data,
            "Event_data": event_Data,
            "Picam_data": PiCam_Data,
            "IR_data": IR_Data,
        }

        #daedalusString = json.dumps(daedalusChunk).encode() + b'\n'
        daedalusDataHandler.write_data(daedalusChunk)

    