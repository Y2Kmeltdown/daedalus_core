import pickle
import cv2
import numpy as np
import event_stream
import pathlib
from tqdm import tqdm

def flatten(xss):
    return [x for xs in xss for x in xs]

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
    data = flatten(data)
    return data


def parseImages(directory:str, pickleData, imageType:str):
    data = [(i["Timestamp"],i[imageType]) for i in pickleData]
    for timestamp, imageList in data:
        if isinstance(imageList, list):
            if len(imageList):
                for n, image in enumerate(imageList):
                    name = f"{directory}/{imageType}_{timestamp}_{n}.png"
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

def parseRawEvents(directory:str, pickleData, dataType:str):
    output_filename = f"{directory}/{dataType}.raw"
    data = [(i["Timestamp"],i[dataType]) for i in pickleData]
    print(len(data))
    eventDataList = []
    for timestamp, eventList in data:
        if isinstance(eventList, list):
            eventBytes = b''.join(eventList)
            eventDataList.append(eventBytes)
    eventData = b''.join(eventDataList)
    with open(output_filename, "wb") as f:
        f.write(eventData)

def decodeEVKArray(evkBytes:bytes):
    event_dtype = [('t', '<u8'), ('x', '<u2'), ('y', '<u2'), ('on', '?')]
    array = np.frombuffer(evkBytes, dtype=event_dtype)
    return array

def encodeESFile(esFilename:str, numpy_array_list):
    encoder = event_stream.Encoder(esFilename, 'dvs', 1280, 720)
    for npy_array in tqdm(numpy_array_list):
        encoder.write(npy_array)

def npyToEs(inputFile, outputFile):
    with open(inputFile, 'rb') as f:
        data = f.read()
    npyArray = decodeEVKArray(data)
    split_arrays = np.array_split(npyArray, 100)
    encodeESFile(outputFile, split_arrays)

if __name__ == "__main__":
    inputFilename="data\\evk4_00050420_data_20250917_144733_1.npy"
    inputFile = pathlib.Path(inputFilename)
    inputStem=inputFile.stem
    outputFile = "recordings\\" + inputStem + ".es"
    npyToEs(inputFile, outputFile)
    #filename = "data/event_synced_data_20250808_150200_1.pickle"
    #pickleData = loadDaedalusPickle(filename)
    #print(pickleData[0].keys())
    #with open("recordings\\testWorking.raw", 'wb') as f:
        #f.write(pickleData[15]["Event_data"][0])
    #parseImages("renders",pickleData,"Picam_data")
    #parseVideo("renders",pickleData,"IR_data")
    #parseRawEvents("recordings", pickleData, "Event_data")