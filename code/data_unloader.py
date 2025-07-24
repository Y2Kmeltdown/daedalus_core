import pickle

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
            print(f"[INFO] All {i} pickles are unzipped. {e} {"Pickles" if e<1 else "Pickle"} {"Weren't" if e<1 else "Wasn't"} preserved.")
            pass
    return data


def getImage(filename:str, data:bytes):
    with open(filename, "wb") as f:
        f.write(data)


def parseImages(directory:str, pickleData, imageType:str):
    data = [(i["Timestamp"],i[imageType]) for i in pickleData]
    for timestamp, imageList in data:
        if isinstance(imageList, list):
            if len(imageList):
                for n, images in enumerate(imageList):
                    name = f"{directory}\{imageType}_{timestamp}_{n}.png"
                    getImage(name, images)

if __name__ == "__main__":
    filename="data/event_synced_data_20250724_112824_1.pickle"
    pickleData = loadDaedalusPickle(filename)
    print(pickleData[0].keys())
    parseImages("data",pickleData,"IR_data")
    parseImages("data",pickleData,"Picam_data")





