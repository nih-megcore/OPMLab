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
from npy2fif_raw import npy2fif_raw
from param import Param, getParam, Str, Bool, Int, Float, Dirname # should just use *, add __all__ @@@
from filters import filt_p, ema, cheby2, nofilt
from sensors import *
from fieldline_api.fieldline_datatype import FieldLineWaveType

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


#%%

# define dynamic field compensation parameters
nResets = 0 # defines the # of repetitions of a fine_zero-dfc block. If 0, the block is repeated once.
fs = 1000 # sampling rate

# other variables
count = 0
g = 1e9  # to convert data into nanotesla

def main(ip_list, flg_restart, flg_cz, flg_fz):
    global done

    # init the calibrator
    onceCoil = False
    if coilID >= 0:
        coil = numato()     # initialize class to energize coil
        coil.deactivate()   # make sure all coils are off
        onceCoil = True

    

    # Get the FieldLine service
    service = FLService(ip_list)

    # Get the full list of sensor (c, s) pairs from the hardware.
    sensID = service.getSensors()

    # sensors we will use as (c, s) pairs, and their indices into sensID
    sensors, refInd, primInd = getIndArrays(sensID, refList, primList)

    # sdict format for talking to the api
    sdict = slist2sdict(sensors)
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
    for ss in range(len(sensors)): 
        print("Now running: chassis " + str(sensors[ss][0]) + ' | sensor ' + str(sensors[ss][1]))
        initWave = True
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
            if initWave:
                if coilType == 0:
                    service.set_bx_wave(sensors[ss][0], sensors[ss][1], FieldLineWaveType.WAVE_SINE, freq, amp)                   
                elif coilType ==1:
                    service.set_by_wave(sensors[ss][0], sensors[ss][1], FieldLineWaveType.WAVE_SINE, freq, amp)                  
                else:
                    service.set_bz_wave(sensors[ss][0], sensors[ss][1], FieldLineWaveType.WAVE_SINE, freq, amp)
                initWave = False

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

        # Out of the while loop.
        # 5.3 | stop clock
        stopped = time.time()-init
        print('tstop:' + str(stopped*1000))       
        print('turning coil ' + coils[coilType] + ' from chassis ' + str(sensID[ss][0]) + ' | sensor ' + str(sensID[ss][1]) + ' off...')

        if coilType == 0:               
            service.set_bx_wave(sensors[ss][0], sensors[ss][1], FieldLineWaveType.WAVE_OFF, freq, amp)
        elif coilType ==1:
            service.set_by_wave(sensors[ss][0], sensors[ss][1], FieldLineWaveType.WAVE_OFF, freq, amp)
        else: 
            service.set_bz_wave(sensors[ss][0], sensors[ss][1], FieldLineWaveType.WAVE_OFF, freq, amp)

        if flgControlC:
            print('bye')
            break

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

        print('saving data...')
        sName = 'chass' + str(sensors[ss][0]) + '_sens' + str(sensors[ss][1]) + '_coil' + coils[coilType] + '_' + str(freq) + 'Hz_' + str(amp) + 'nT'

        sPath = f"./{savePath}/" + sName
        chNs = chNames_Ref + chNames_Prim # add ADC name here

        np.save(sPath + '_rawRef', f_raw_Ref)
        np.save(sPath + '_rawPrim', f_raw_Prim)
        np.save(sPath + '_rawADC', f_raw_adc)
        np.save(sPath + '_FZcoeffs', np.array(fzCoeffs))
        if flg_fz:
            np.save(sPath + '_FZcoeffs0', np.array(fzCoeffs0))
        if flg_cz:
            matCZ = np.array(czCoeffs)
            np.save(sPath + '_CZcoeffs', matCZ)
        np.save(sPath + '_calib', calib)              
        npy2fif_raw(sPath, f_raw_adc, f_raw_Ref, f_raw_Prim, chNs, calib)
        
        print('done.')


if __name__ == "__main__":

    # Load a standard parser, add some extra parameters, and merge in the special parsers.

    p = Param()

    p.register("ipList", 'i', Str(), help="Comma separated list of IPs")
    p.register("restart", 'r', Bool(), help="Flag to restart sensors.", default=False)
    p.register("coarseZero", 'c', Bool(), help="Flag to coarse zero sensors.", default=False)
    p.register("fineZero", 'f', Bool(), help="Flag to fine zero sensors.", default=False)
    p.register("savePath", None, Dirname(create=True), arghelp="DIR", help="Path to save data.")
    p.register("coilID", 'C', Int(), default=-1, arghelp="N", help="Calibrator coil id. Default none (-1).")
    p.register("duration", 't', Float(), default=0, arghelp="DUR", help="Length of recording in seconds.")
    p.register("closedLoop", None, Bool(), default=True, help="Whether to use closed loop, default true.")
    p.register("frequency", '-fr', Float(), help="Frequency of sine wave (Hz)",default=10)
    p.register("amplitude", '-a', Float(), help="Peak to peak amplitude of sine wave (nT)", default=1)
    p.register('coilType', '-ct', Int(), help = "coil to energize: 0=bx; 1=by;[2]=bz",default=2)
  
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

    # Enable logging and write the parameters to the log file.

    p.enableLogging()
    p.logParam()

    # convenient names for things

    flg_restart = p.restart
    flg_cz = p.coarseZero
    flg_fz = p.fineZero
    savePath = p.savePath
    coilID = p.coilID
    refList = p.RefList
    primList = p.PrimList
    ADCList = p.ADCList
    closedLoop = p.closedLoop
    nRef = len(refList)
    nPrim = len(primList)
    nADC = len(ADCList)
    coilType = p.coilType
    freq = p.frequency
    amp = p.amplitude
    td = p.duration
    coils = ['bx','by', 'bz']
    # Convert ADCList to a list of just the chassis numbers.

    ADCchas = slist2clist(ADCList)

    print("Connecting to IPs:", ip_list)
    print("flg_restart", flg_restart)
    print("flg_cz", flg_cz)
    print("flg_fz", flg_fz)
    print("savePath", savePath)

    main(ip_list, flg_restart, flg_cz, flg_fz)

    print("exit")
    sys.exit(0)
