#! /usr/bin/env python

import logging
import threading
import queue
import time
import sys
import string
import numpy as np
import signal
import copy

from service import FLService
from numato import numato
from npy2fif import npy2fif
from param import *
from filters import *
from sensors import *

#%%

"""
Dynamic field compensation (dfc) for every incoming sample.
This process consists of:
1. Get sample (sample = data*calibration coefficient [in T])
2. Compute exponential moving average
3. Compute compensation fields using predefined 'rotation' matrices
4. Apply compensation fields
"""

# Handle ^C

flgControlC = False
def handler(signum, frame):
    global flgControlC
    flgControlC = 1

signal.signal(signal.SIGINT, handler)

class DimError(ValueError):
    def __str__(self):
        return 'dimension mismatch: dictInd and primInd are not of the same length'

def loadRotMat_RefSens():
    """
    Load pre-computed rotation matrices for reference sensors (I,J,K).
    The I,J,K sensors are placed in the IJK coordinate system we need
    to translate the measured fields in the IJK coordinate system
    onto the xyz coordinate system where the bx,by,bz coils of
    each sensor is defined. The last row of the rot matrices was ommited
    since we don't need to adjust the bz coil of the ref sensors.
    """

    Rot_RefI = np.zeros([2, 3])
    Rot_RefI[0, 1], Rot_RefI[1, 2] = 1, 1

    Rot_RefJ = np.zeros([2, 3])
    Rot_RefJ[0, 0], Rot_RefJ[1, 2] = 1, -1

    Rot_RefK = np.zeros([2, 3])
    Rot_RefK[0, 1], Rot_RefK[1, 0] = 1, -1

    return Rot_RefI, Rot_RefJ, Rot_RefK


def getCompField_Ref(R, filt_f, g):
    """
    compute compensation fields for transverse coils of reference sensors
    input parameters:
    - R: pre-loaded rotation matrix of ref sensors I,J,K
    - filt_f: filtered measured reference fields
    - g: scaling factor to transform values to nT
    """

    compensat_f = g * R.dot(filt_f)
    bx = compensat_f[0]  # compensation to be applied on x coil
    by = compensat_f[1]  # compensation to be applied on y coil

    return bx, by


def loadRotMat_PrimSens():
    """
    load pre-computed rotation matrices for primary sensors
    """

    f = open('RefinedAxes.txt', 'r') # open('OPM_Axes_New.txt', 'r')
    Lines = f.readlines()

    count = 1
    primRotMat = np.zeros([16,3,3])
    # Strips the newline character
    for line in Lines:

        if line in str(count)+'\n': # sensor number
            count+=1
            row = 0
            matr = np.zeros([3,3])
        else:
            matr[row,:] = np.array(line.split(),dtype=float)
            if row==2:
                primRotMat[count-2,:,:]=matr
            row +=1

    return primRotMat


def getCompField_Prim(R, filt_f, g):
    """
    compute compensation fields for transverse coils of reference sensors
    input parameters:
    - R: pre-loaded rotation matrix of primary sensors
    - filt_f: filtered measured reference fields
    - g: scaling factor to transform values to nT
    """

    compensat_f = g * R.dot(filt_f)
    bx = compensat_f[0]  # compensation to be applied on x coil
    by = compensat_f[1]  # compensation to be applied on y coil
    bz = compensat_f[2]  # compensation to be applied on z coil

    return bx, by, bz

#%%

tCoilStart = 0 # in seconds

# define dynamic field compensation parameters

nResets = 0 # defines the # of repetitions of a fine_zero-dfc block. If 0, the block is repeated once.

fs = 1000 # sampling rate

# other variables
count = 0
g = 1e9  # to convert data into nanotesla

def main(ip_list, flg_restart, flg_cz, flg_fz, sName):
    global done

    # init the calibrator
    onceCoil = False
    if coilID >= 0:
        coil = numato()     # initialize class to energize coil
        coil.deactivate()   # make sure all coils are off
        onceCoil = True

    # load rotation matrices
    rot_RefI, rot_RefJ, rot_RefK = loadRotMat_RefSens() # load rot matrices
    primRotMat = loadRotMat_PrimSens()

    # Get the FieldLine service
    service = FLService(ip_list)

    # Get the full list of sensor (c, s) pairs from the hardware.
    sensID = service.getSensors()

    # sensors we will use as (c, s) pairs, and their indices into sensID
    sensors, refInd, primInd = getIndArrays(sensID, refList, primList)

    # sdict format for talking to the api
    sdict = slist2sdict(sensors)

    dfcInd = primInd    # @@@ parameter
    nDfc = len(dfcInd)

    # This sensor dict is for talking to adjust_fields()
    sensor_dict = {}
    chassID = slist2clist(sensors)

    # run restart | coarse | fine zeroing
    if flg_restart:
        service.restartSensors(sdict, closedLoop)
    if flg_cz:
        service.coarseZero(sdict)
        czCoeffs = service.getCoeffs(sdict)
        print('after coarse zero', czCoeffs)
    if flg_fz:
        service.fineZero(sdict)
        fzCoeffs0 = service.getCoeffs(sdict)
        print('after fine zero', fzCoeffs0)

    # load additional setup parameters
    chNames, calib = service.getSensorInfo(sdict, closedLoop)

    print('loaded sensor IDs:', sensID)
    print('sensors:', sensors)
    print('sdict:', sdict)

    # Get channel names and calibration values by type.

    chNames_Ref = []
    calib_Ref = []
    for sens in refInd:
        chNames_Ref.append(chNames[sensID[sens]])
        if len(calib) != 0:
            calib_Ref.append(calib[sensID[sens]])
    print('References:', chNames_Ref)
    print('Calibrations:', calib_Ref)

    chNames_Prim = []
    calib_Prim = []
    for sens in primInd:
        chNames_Prim.append(chNames[sensID[sens]])
        if len(calib) != 0:
            calib_Prim.append(calib[sensID[sens]])
    print('Primaries:', chNames_Prim)
    print('Calibrations:', calib_Prim)

    # initialize lists for saving data
    f_raw_Ref = []
    f_raw_Prim = []
    f_raw_adc = []
    f_filt = []
    f_compRef = []
    f_compPrim = []
    f_gradPrim = []
    f_coeffs = []

    q = queue.Queue(50) # queue is needed to access bz data outside the getData callback

    def getData(data):
        """
        This function is a callback to read the data structure in the stream.
        The data is saved on a queue that can be accessed outside of this function.
        The variable count counts the total number of samples.
        """
        global count
        count += 1
        q.put(data)

    print("Press Enter")
    sys.stdin.read(1)

    for c in ADCchas:
        service.start_adc(c)

    fztime = []
    for n in range(nResets+1): # this block does fine zeroing before the dfc is started

        # Get ready to energize the coil as quickly as possible.

        if coilID >= 0:
            coil.preactivate(coilID)

        rawDataRef = np.zeros(nRef)
        rawDataPrim = np.zeros(nPrim)
        adcData = np.zeros(nADC)

        print(f"Doing fine zero {n}")
        tfz0 = time.time()
        service.fineZero(sdict)
        fztime.append(time.time() - tfz0)

        service.read_data(getData)  # begin collecting data

        t0 = None
        init = time.time()
        while time.time()-init < td: # do dfc for td seconds

            if onceCoil:
                if coilID >= 0:
                    # energize the coil
                    coil.go()
                    onceCoil = False

            # 1 | get raw data from queue
            try:
                data = q.get(timeout=0.5)

                for sens in range(nRef):
                    rawDataRef[sens] = data['data_frames'][chNames_Ref[sens]]['data']*calib_Ref[sens]*g

                for sens in range(nPrim):
                    rawDataPrim[sens] = data['data_frames'][chNames_Prim[sens]]['data']*calib_Prim[sens]*g

                for i, c in enumerate(ADCchas):
                    name = f"{c:02d}:00:0"
                    adcData[i] = data['data_frames'][name]['data']*2.980232238769531e-07 # @@@ give this a name

                timestamp = data['timestamp']/25*1e3 # api uses a sampling rate of 25MHz
                if t0 is None:
                    t0 = timestamp / 1000
                if count % 100 == 0:
                    print(timestamp / 1000 - t0)

                f_raw_Ref.append(list(np.insert(rawDataRef,0,time.time()-init)))
                f_raw_Prim.append(list(rawDataPrim))
                f_raw_adc.append(list(adcData))

            except queue.Empty:
                print("empty")
                continue

            # 1.1 | reinitialize the dict for adjust_fields()

            for c in chassID:
                sensor_dict[c] = []

            # 2 | filter the reference sensors

            if refInd:
                filt_f = filter_ref(rawDataRef)
                f_filt.append(filt_f)

                # 3 | compute & save compensation fields

                # 3.1 | Ref sensors
                bx_I, by_I = getCompField_Ref(rot_RefI, filt_f, 1)
                bx_J, by_J = getCompField_Ref(rot_RefJ, filt_f, 1)
                bx_K, by_K = getCompField_Ref(rot_RefK, filt_f, 1)

                if runDFC > 0:
                    c = sensID[refInd[0]][0] # @@@ all references have to be on the same chassis
                    sensor_dict[c].append((sensID[refInd[0]][1], -bx_I, -by_I, None))
                    sensor_dict[c].append((sensID[refInd[1]][1], -bx_J, -by_J, None))
                    sensor_dict[c].append((sensID[refInd[2]][1], -bx_K, -by_K, None))

                # 3.1.1 | save compensation values onto compRef matrix

                compRef = np.zeros([nRef,2])
                compRef[0,0], compRef[0,1] = bx_I, by_I
                compRef[1,0], compRef[1,1] = bx_J, by_J
                compRef[2,0], compRef[2,1] = bx_K, by_K
                f_compRef.append(compRef)

            # 3.2 | Primary sensors

            compPrim = np.zeros([nPrim, 3])
            gradPrim = np.zeros(nPrim)
            for sens in range(nPrim):
                # the sensor # within the chassis is the index into array of rotation matrices
                # index origin 0
                c, s = sensID[primInd[sens]]
                bx, by, bz = getCompField_Prim(primRotMat[s-1], filt_f, 1)

                compPrim[sens,:] = np.array([bx, by, bz])   # save compensation values
                gradPrim[sens] = rawDataPrim[sens] - bz     # compute 1st-order gradiometer

                # record compensation for selected primary sensors
                if runDFC > 1 and (primInd[sens] in dfcInd):
                    sensor_dict[c].append((s, -bx, -by, None))

            f_compPrim.append(compPrim)
            f_gradPrim.append(gradPrim)

            if runDFC > 0:
                # 4 | call adjust_fields()
                service.adjust_fields(sensor_dict) # apply compensation field

            if flgControlC:
                print('bye')
                break

        # Out of the while loop.

        # 5 | reset calls

        if runDFC > 0:
            # 5.1 | reset adjust_fields()
            # use the last sensor dict
            for c in chassID:
                for i in range(len(sensor_dict[c])):
                    sensor_dict[c][i] = (sensor_dict[c][i][0], 0, 0, 0)
            service.adjust_fields(sensor_dict)

        # 5.2 | stop getdata callback
        service.read_data()

        # 5.3 | deactivate coil
        if coilID >= 0:
            print("turning coil off")
            coil.deactivate()
            onceCoil = True

    fztime = np.array(fztime)
    print("fztime:", fztime.mean(), fztime.std())

    # Get the final fine zero values.
    fzCoeffs = service.getCoeffs(sdict)

    if coilID >= 0:
        coil.close()

    for c in ADCchas:
        service.stop_adc(c)

    # 6 | convert lists onto numpy arrays & save them

    f_raw_Ref = np.array(f_raw_Ref)
    f_raw_Prim = np.array(f_raw_Prim)
    f_raw_adc = np.array(f_raw_adc)
    f_filt = np.array(f_filt)

    f_compRef = np.array(f_compRef)
    f_compPrim = np.array(f_compPrim)
    f_gradPrim = np.array(f_gradPrim)

    print('saving data...')
    sPath = f"./{savePath}/" + prefix + sName
    chNs = chNames_Ref + chNames_Prim # add ADC name here

    np.save(sPath + '_rawRef', f_raw_Ref)
    np.save(sPath + '_rawPrim', f_raw_Prim)
    np.save(sPath + '_rawADC', f_raw_adc)
    np.save(sPath + '_filt', f_filt)
    np.save(sPath + '_compRef', f_compRef)
    np.save(sPath + '_compPrim', f_compPrim)
    np.save(sPath + '_gradPrim', f_gradPrim)
    np.save(sPath + '_FZcoeffs', np.array(fzCoeffs))
    if flg_fz:
        np.save(sPath + '_FZcoeffs0', np.array(fzCoeffs0))
    if flg_cz:
        matCZ = np.array(czCoeffs)
        np.save(sPath + '_CZcoeffs', matCZ)
    np.save(sPath + '_refInd', refInd)
    np.save(sPath + '_dfcInd', dfcInd)
    np.save(sPath + '_primInd', primInd)
    np.save(sPath + '_chanNames', chNs)
    np.save(sPath + '_calib', calib)

    npy2fif(sPath, sensID, f_raw_adc, f_raw_Ref, f_raw_Prim, chNs, calib, f_compRef, f_compPrim, f_gradPrim, np.array(fzCoeffs))

    print('done.')


if __name__ == "__main__":

    # Load a standard parser, add some extra parameters, and merge in the special parsers.

    p = Param()

    p.register("ipList", 'i', Str(), help="Comma separated list of IPs")
    p.register("restart", 'r', Bool(), help="Flag to restart sensors.", default=False)
    p.register("coarseZero", 'c', Bool(), help="Flag to coarse zero sensors.", default=False)
    p.register("fineZero", 'f', Bool(), help="Flag to fine zero sensors.", default=False)
    p.register("saveName", 's', Str(), arghelp="NAME", help="prefix name to save data.")
    p.register("savePath", None, Dirname(create=True), arghelp="DIR", help="Path to save data.")
    p.register("runDFC", 'd', Int(), default=0, arghelp="N", help="0 (noDFC, default), 1 (refDFC), or 2 (primDFC).")
    p.register("coilID", 'C', Int(), default=-1, arghelp="N", help="Calibrator coil id. Default none (-1).")
    p.register("duration", 't', Float(), default=0, arghelp="DUR", help="Length of recording in seconds.")
    p.register("closedLoop", None, Bool(), default=True, help="Whether to use closed loop, default true.")

    p.registryMerge(sens_p)     # sensor list parameters
    p.registryMerge(filt_p)     # filter parameters

    # Get all the parameters from the command line, environment, and parameter files.

    try:
        p = getParam(p)
    except Exception as e:
        print(e)
        sys.exit(1)

    # Sanity checks

    if not p.ipList:
        p.err("--ip is required")
    ip_list = p.ipList.split(',')

    if not p.saveName:
        p.saveName = 'test'

    # Enable logging and write the parameters to the log file.

    p.enableLogging()
    p.logParam()

    # convenient names for things

    flg_restart = p.restart
    flg_cz = p.coarseZero
    flg_fz = p.fineZero
    saveName = p.saveName
    savePath = p.savePath
    runDFC = p.runDFC
    coilID = p.coilID
    filter = p.FilterType
    refList = p.RefList
    primList = p.PrimList
    ADCList = p.ADCList
    closedLoop = p.closedLoop
    nRef = len(refList)
    nPrim = len(primList)
    nADC = len(ADCList)

    td = p.duration

    # Convert ADCList to a list of just the chassis numbers.

    ADCchas = slist2clist(ADCList)

    # Save the DFC type in the output filename.

    if p.runDFC == 0:
        prefix = 'noDFC_'
    elif p.runDFC == 1:
        prefix = 'refDFC_'
    else:
        prefix = 'primDFC_'

    # Create the filter for the references.

    if filter[0] == 'e':
        tau = filter[1]
        filter_ref = ema(nRef, tau)
    elif filter[0] == 'c':
        cutoffFreq, order, dB = filter[1:]
        filter_ref = cheby2(nRef, cutoffFreq, N=order, dB=dB)
    elif filter[0] == 'E':
        cutoffFreq, order, rp, dB = filter[1:]
        filter_ref = elliptic(nRef, cutoffFreq, N=order, rp=rp, dB=dB)
    elif filter[0] == 'n':
        filter_ref = nofilt(nRef)
    else:
        print(f"Unknown filter type {filter}.")
        sys.exit(1)

    print("Connecting to IPs:", ip_list)
    print("flg_restart", flg_restart)
    print("flg_cz", flg_cz)
    print("flg_fz", flg_fz)
    print("savePath", savePath)
    print("saveName", saveName)
    print("runDFC", runDFC)

    main(ip_list, flg_restart, flg_cz, flg_fz, saveName)

    print("exit")
    sys.exit(0)
