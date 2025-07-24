# #To append to a pickle file
import pickle

# p={1:2}
# q={3:4}

filename="data/event_synced_data_20250724_110258_1.pickle"
# with open(filename, 'ab+') as fp:
#     pickle.dump(p,fp)
#     pickle.dump(q,fp)


#To load from pickle file
data = []
with open(filename, 'rb') as fr:
    try:
        while True:
            test = pickle.load(fr)
            print(test)
            data.append(test)
    except EOFError:
        pass


