import pickle
from os.path import exists, split
from constants import *
import logging

        
    
def configure_logging(p, mode):


    fh = logging.FileHandler(f"{p.sPath}_exp.txt", mode)
    formatter = logging.Formatter("%(filename)s:%(lineno)d | %(message)s")
                                  #%(asctime)s | %(message)s',
                                  #'%d/%m/%Y %H:%M:%S')
    fh.setFormatter(formatter)
    
    f = testFilter()
    
    root = logging.getLogger(name='DFClog')

    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addFilter(f)
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    # set format for console output    
    console.setFormatter(logging.Formatter("%(message)s"))

    # add the handler to the root logger
    root.addHandler(console)
    root.propagate = False
    return root

   

class testFilter(logging.Filter):
    
    def filter(self, record):
        #print(record.name, record.getMessage())
        return record.name == 'DFClog'


def savePickle(data, savingPath):

    # open a file, where you ant to store the data
    file = open(savingPath,'wb')

    # dump information to that file
    pickle.dump(data, file)

    # close the file
    file.close()


def loadPickle(file):
      
    with open(file, 'rb') as file:

        # Call load method to deserialze
        var = pickle.load(file)

    st = struct()

    for key in var.__dict__.keys():
        setattr(st, key, var.__dict__[key])


    return st


