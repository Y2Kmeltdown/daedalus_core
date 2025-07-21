import neuromorphic_drivers as nd
import time
import numpy as np

configuration = nd.prophesee_evk4.Configuration(
        biases=nd.prophesee_evk4.Biases(
            diff_off=80,  # default: 102
            diff_on=140,  # default: 73
        )
)

evkSerialList = nd.list_devices()
evkSerial = evkSerialList[0].serial

with nd.open(serial=evkSerial) as device:
    event_cam_width = device.properties().width
    event_cam_height = device.properties().height


eventCamShape = (event_cam_height, event_cam_width, 2)

frame = np.zeros(
        (event_cam_height, event_cam_width),
        dtype=np.uint8,
    )+127
oldTime = time.monotonic_ns()

try:
    with nd.open(serial=evkSerial, configuration=configuration) as device:
        print(f"Successfully started EVK4 {evkSerial}")
        timeEnd = 0
        timeStart = 0

        procTimeStart = 0
        procTimeEnd = 0
        for status, packet in device:
            timeEnd = time.monotonic_ns()
            extForLoopTime = timeEnd-timeStart
            print(f"External For Loop Time:{extForLoopTime}")
            
            procTimeStart = time.monotonic_ns()
            if "dvs_events" in packet:
                print(f"Length of Packet: {len(packet["dvs_events"])}")
                frame[
                    packet["dvs_events"]["y"],
                    packet["dvs_events"]["x"],
                ] = packet["dvs_events"]["on"]*255

                if time.monotonic_ns()-oldTime >= (1/50)*1000000000:

                    data = frame.tobytes()

                    frame = np.zeros(
                        (event_cam_height, event_cam_width),
                        dtype=np.uint8,
                    )+127
                    oldTime = time.monotonic_ns()
            procTimeEnd = time.monotonic_ns()
            intForLoopTime = procTimeEnd-procTimeStart
            print(f"Internal For Loop Time:{intForLoopTime}")
            timeStart = time.monotonic_ns()
            
except KeyboardInterrupt:
    print("Keyboard Interupt")