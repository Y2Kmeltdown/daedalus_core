import neuromorphic_drivers as nd
import numpy as np

configuration = nd.prophesee_evk4.Configuration(
    biases=nd.prophesee_evk4.Biases(
        diff_off=102,  # default: 102
        diff_on=73,    # default: 73
    )
)

with nd.open(serial="00051501", configuration=configuration) as device:
    cam_width = device.properties().width
    cam_height = device.properties().height
    frame = np.zeros(
        (cam_height, cam_width),
        dtype=np.float32,
    )+127
    for status, packet in device:
        if packet:
            frame[
            packet["dvs_events"]["y"],
            packet["dvs_events"]["x"],
            ] = packet["dvs_events"]["on"]*255
            print(frame)
            

        