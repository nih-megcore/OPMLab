# Program to save a NumPy array to a text file
 
import numpy as np
import os

files = os.listdir()

NrReps = 20

for file in files:
    for nn in range(NrReps+1):
        if file.endswith('FZcoeffsRep' + str(nn) + '.npy'):
            print(nn,file)
            tmp = file[:-4] + '.txt'
            f = open(tmp, "w+")
            Array = np.load(file)
            content = str(Array)
            f.write(content)
            f.close()

for file in files:
    if file.endswith('CZcoeffs.npy'):
        print(file)
        tmp = file[:-4] + '.txt'
        f = open(tmp, "w+")
        Array = np.load(file)
        content = str(Array)
        f.write(content)
        f.close()

for file in files:
    if file.endswith('FZcoeffs.npy'):
        print(file)
        tmp = file[:-4] + '.txt'
        f = open(tmp, "w+")
        Array = np.load(file)
        content = str(Array)
        f.write(content)
        f.close()

for file in files:
    if file.endswith('FZcoeffs0.npy'):
        print(file)
        tmp = file[:-4] + '.txt'
        f = open(tmp, "w+")
        Array = np.load(file)
        content = str(Array)
        f.write(content)
        f.close()

