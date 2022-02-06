#! /usr/bin/env python

import argparse
import time
import sys, os
import numpy as np
import pyctf
import matplotlib.pyplot as plt

def loadRotMat_RefSens():
    """
    load pre-computed rotation matrices for reference sensors (I,J,K)
    the I,J,K sensors are placed in the IJK coordinate system
    we need to translate the measured fields in the IJK coordinate system onto the xyz coordinate system
    where the bx,by,bz coils of each sensors are defined  
    """
       
    Rot_RefI = np.zeros([2,3])
    Rot_RefI[0,1], Rot_RefI[1,2] = 1, 1
    
    Rot_RefJ = np.zeros([2,3])
    Rot_RefJ[0,0], Rot_RefJ[1,2] = 1, -1
    
    Rot_RefK = np.zeros([2,3])
    Rot_RefK[0,1], Rot_RefK[1,0] = 1, -1
    
    return Rot_RefI, Rot_RefJ, Rot_RefK

def getCompField_Ref(R,mav,g):
    
    """
    compute compensation fields for transverse coils of reference sensors
    input parameters:
    - R: pre-loaded rotation matrix of ref sensors I,J,K
    - mav: moving average of measured reference fields
    - g: current delivered by the D/A converters [3x1] - only needed if input units are not nanotesla
    """
    measured_f = mav.T # [3x1]
    compensat_f = g*(R.dot(measured_f)) # [3x1]
    bx = compensat_f[0] # compensation to be applied on x coil
    by = compensat_f[1] # compensation to be applied on y coil
    #bz = compensat_f[2] # compensation to be applied on z coil
    
    return bx,by

def ema(data, a):
    """
    compute exponential moving average
    input parameters:
    - data: newest sample
    - a: time decay
    """
    global mav
    mav = a*mav + (1-a)*data

mav = np.zeros([1,3])
tau = 0.01 # 10 ms
fs = 1000
a = np.e**(-1/(fs*tau))
g = 1e9 # to convert data into nanotesla

rot_RefI, rot_RefJ, rot_RefK = loadRotMat_RefSens() # load rotation matrices

"""
Do the dynamic field compensation (dfc) for every incoming sample. This process consists of:
1. Get sample (sample = data*calibration coefficient [T])
2. Compute exponential moving average
3. Compute compensation fields using predefined 'rotation' matrices
4. Apply compensation fields

"""

# 1 | get raw data

ds = pyctf.dsopen(os.getenv('ds'))
rawdata = ds.getRefArray(0)

# 2 | compute moving average of data

bx_I = []
by_I = []
bx_J = []
by_J = []
bx_K = []
by_K = []
mav_I = []
mav_J = []
mav_K = []

for data in rawdata.T:
    ema(data, a) # the output of this is mav

    mav_I.append(mav[0,0]*g)
    mav_J.append(mav[0,1]*g)
    mav_K.append(mav[0,2]*g)
    
    # 3 | compute compensation fields
    
    x_I, y_I = getCompField_Ref(rot_RefI, mav, g)
    x_J, y_J = getCompField_Ref(rot_RefJ, mav, g)
    x_K, y_K = getCompField_Ref(rot_RefK, mav, g)

    bx_I.append(-x_I)
    by_I.append(-y_I)
    bx_J.append(-x_J)
    by_J.append(-y_J)
    bx_K.append(-x_K)
    by_K.append(-y_K)

plt.subplot(431)
plt.plot(rawdata[0]*g)
plt.subplot(432)
plt.plot(rawdata[1]*g)
plt.subplot(433)
plt.plot(rawdata[2]*g)

plt.subplot(434)
plt.plot(mav_I)
plt.subplot(435)
plt.plot(mav_J)
plt.subplot(436)
plt.plot(mav_K)

plt.subplot(437)
plt.plot(bx_I)
plt.subplot(438)
plt.plot(bx_J)
plt.subplot(439)
plt.plot(bx_K)

plt.subplot(4,3,10)
plt.plot(by_I)
plt.subplot(4,3,11)
plt.plot(by_J)
plt.subplot(4,3,12)
plt.plot(by_K)

plt.show()