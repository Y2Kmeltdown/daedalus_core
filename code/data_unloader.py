import pickle
import cv2
import numpy as np

def loadDaedalusPickle(filename:str):
    data = []
    with open(filename, 'rb') as fr:
        i = 0
        e = 0
        try:
            while True:
                try:
                    test = pickle.load(fr)
                    data.append(test)
                except pickle.UnpicklingError as err:
                    e+=1
                    print(f"[ERROR] Pickle caught in zipper! Object {i} might be corrupt or incomplete.")
                i+=1
        except EOFError:
            i-=1
            print(f"[INFO] All {i} pickles are unzipped. {e} {'Pickles' if e<1 else 'Pickle'} {'Werent' if e<1 else 'Wasnt'} preserved.")
            pass
    return data


def parseImages(directory:str, pickleData, imageType:str):
    data = [(i["Timestamp"],i[imageType]) for i in pickleData]
    for timestamp, imageList in data:
        if isinstance(imageList, list):
            if len(imageList):
                for n, image in enumerate(imageList):
                    name = f"{directory}\{imageType}_{timestamp}_{n}.png"
                    with open(name, "wb") as f:
                        f.write(image)

def parseVideo(directory:str, pickleData, imageType:str):
    data = [(i["Timestamp"],i[imageType]) for i in pickleData]
    output_filename = f"{directory}/{imageType}.avi"
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = 15
    frame_width = 640
    frame_height = 480
    frame_size = (frame_width, frame_height)
    out = cv2.VideoWriter(output_filename, fourcc, fps, frame_size, isColor=False)
    for timestamp, imageList in data:
        if isinstance(imageList, list):
            if len(imageList):
                for n, image in enumerate(imageList):
                    np_array = np.frombuffer(image, np.uint8)
                    outframe = cv2.imdecode(np_array, -1)
                    out.write(outframe)
    out.release()
    print(f"Video saved as {output_filename}")

if __name__ == "__main__":
    #filename="D:\\event_synced\\event_synced_data_20250728_163508_2.pickle"
    filename = "data/event_synced_data_20250808_145033_1.pickle"
    pickleData = loadDaedalusPickle(filename)
    print(pickleData[0].keys())
    #parseImages("data",pickleData,"IR_data")
    parseVideo("data",pickleData,"IR_data")
    #parseImages("data",pickleData,"Picam_data")





