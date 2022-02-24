#! /usr/bin/env python

from fieldline_api.fieldline_service import FieldLineService
from fieldline_api.pycore.hardware_state import HardwareState
from fieldline_api.pycore.sensor import SensorInfo, ChannelInfo

import logging
import threading
import queue
import time
import sys
import string
import numpy as np
import signal
import copy
from numato import numato
from npy2fif import npy2fif
from param import Param, getParam, Str, Bool, Int
from filters import filt_p, ema, cheby2, nofilt
from sensors import sens_p, getSensorInfo, slist2clist, getIndArrays

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

# Generic "done" callback

done = False
def call_done():
    global done
    done = True

class DimError(ValueError):
    def __str__(self):
        return 'dimension mismatch: dictInd and primInd are not of the same length'


def restart_sensors(ip_list):

    global done
    try:
        with FieldLineService(ip_list) as service:
            done = False
            # Get dict of all the sensors
            sensors = service.load_sensors()

            print(f"Got sensors: {sensors}")

            print("Doing sensor restart")
            # Do the restart
            service.restart_sensors(sensors,
                                    on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished restart'),
                                    on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                    on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

            if closedLoop:
                # Make sure closed loop is set
                service.set_closed_loop(True)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))


def coarse_zero(ip_list):

    global done
    try:
        with FieldLineService(ip_list) as service:
            done = False
            sensors = service.load_sensors()
            print(f"Got sensors: {sensors}")
            time.sleep(2)
            print("Doing coarse zero")
            service.coarse_zero_sensors(sensors,
                                        on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished coarse zero'),
                                        on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                        on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))


def fine_zero(ip_list):

    global done
    try:
        with FieldLineService(ip_list) as service:
            done = False

            sensors = service.load_sensors()
            print(f"Got sensors: {sensors}")
            print("Doing fine zero")
            service.fine_zero_sensors(sensors,
                                        on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                                        on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                        on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))


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

dfcInd = range(15) #[1,3,4,6,9,11,12,13]#range(15)
nDfc = len(dfcInd)

tCoilStart = 0 # in seconds

#runDFC = 0 # 0: don't run DFC; 1: run for Refs only; 2: run for primary and refs sensors
closedLoop = 1 # 0: open loop (OL); 1: closed loop

# define dynamic field compensation parameters
td = 30 # duration of applied compensation segment [in seconds]
nResets = 0 # defines the # of repetitions of a fine_zero-dfc block. If 0, the block is repeated once.

fs = 1000 # sampling rate

# get dictionary index for adjust_fields()
sArr = range(1,17) # this is the default sensor id per chassis. It is one-based
"""
if faultySens:
    dictInd = np.setdiff1d(sArr, faultySens+1)
else:
    dictInd = sArr
try:
    if len(dictInd)!= len(primInd):
        raise DimError
except DimError as err:
    print(err)
"""

# other variables
count = 0
g = 1e9  # to convert data into nanotesla


def main(ip_list, flg_restart, flg_cz, flg_fz, sName):

    global sensor_dict

    onceCoil = False
    if coilID >= 0:
        coil = numato()     # initialize class to energize coil
        coil.deactivate()   # make sure all coils are off
        onceCoil = True

    # run restart | coarse | fine zeroing
    if flg_restart:
        restart_sensors(ip_list)
    if flg_cz:
        coarse_zero(ip_list)
    if flg_fz:
        fine_zero(ip_list)

    # load rotation matrices
    rot_RefI, rot_RefJ, rot_RefK = loadRotMat_RefSens()  # load rot matrices
    primRotMat = loadRotMat_PrimSens()

    """
    if faultySens:
        print(primRotMat.shape)
        primInd2 = range(0,16)
        indx = list(np.setdiff1d(primInd2,np.array(faultySens)))
        print(indx)
        primRotMat = primRotMat[indx,:,:]
        print(primRotMat.shape)
    """

    # load additional setup parameters
    global calib, chassID, sensID
    chassID, sensID, chNames, calib = getSensorInfo(ip_list)

    # sensors we will use, and their indices into sensID
    sensors, refInd, primInd = getIndArrays(sensID, refList, primList)

    # define sensor_dict for adjust_fields()
    if (np.array(refInd)>15).any():     # @@@
        cI = 1
    else:
        cI = 0

    if runDFC == 1:
        cInd = [chassID[cI]]
        sensor_dict = {}
        for c in cInd:
            sensor_dict[c] = [None]*len(refInd)
    else:
        sensor_dict = {}
        for c in chassID:
            if c == chassID[0]:
                sensor_dict[c] = [None]*len(dfcInd)
            else:
                sensor_dict[c] = [None]*len(refInd)


    print('loaded sensor IDs:', sensID)
    print('channel names', chNames)
    print('calibration values:', calib)
    print('len calib ', len(calib) , 'len sens ', len(list(primInd)+refInd))
    print('sensors:', sensors)
    print('chassis ID:', chassID)

    # get channel names
    chNames_Ref = []
    for sens in refInd:
        chNames_Ref.append(chNames[sens])

    print(chNames_Ref)

    chNames_Prim = []
    for sens in primInd:
        chNames_Prim.append(chNames[sens])

    print(chNames_Prim)

    # initialize lists for saving data
    f_raw_Ref = []
    f_raw_Prim = []
    f_raw_adc = []
    f_filt = []
    f_compRef = []
    f_compPrim = []
    f_gradPrim = []
    f_coeffs = []

    print("acquire service")
    with FieldLineService(ip_list) as service:
        q = queue.Queue(10) # queue is needed to access bz data outside the getData callback

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

        global done
        for n in range(nResets+1): # this block does fine zeroing before the dfc is started

            done = False
            print(f"Doing fine zero {n}")
            sensors = service.load_sensors()
            service.fine_zero_sensors(sensors,
                                        on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                                        on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                        on_completed=lambda: call_done())
            while not done:
                time.sleep(0.01)

            print("setting dfc")

            init = time.time()
            started = time.time()-init
            print('tstart: ' + str(started*fs))

            service.read_data(getData)  # begin collecting data
            #time.sleep(.001)

            rawDataRef = np.zeros(nRef)
            rawDataPrim = np.zeros(nPrim)
            adcData = np.zeros(nADC)
            t0 = None
            while time.time()-init < td: # do dfc for td seconds

                if count >= int(tCoilStart*fs) and onceCoil:
                    if coilID >= 0:
                        # energize coil
                        coil.energize(coilID)
                        onceCoil = False

                # 1 | get raw data from queue
                try:
                    data = q.get(timeout=0.5)

                    for sens in range(nRef):
                        rawDataRef[sens] = data['data_frames'][chNames_Ref[sens]]['data']*calib[refInd[sens]]*g

                    for sens in range(nPrim):
                        rawDataPrim[sens] = data['data_frames'][chNames_Prim[sens]]['data']*calib[primInd[sens]]*g

                    for i, c in enumerate(ADCchas):
                        name = f"{c:02d}:00:0"
                        adcData[i] = data['data_frames'][name]['data']*2.980232238769531e-07

                    timestamp = data['timestamp']/25*1e3 # api uses a sampling rate of 25MHz
                    if t0 is None:
                        t0 = timestamp / 1000
                    print(timestamp / 1000 - t0)

                    f_raw_Ref.append(list(np.insert(rawDataRef,0,time.time()-init)))
                    f_raw_Prim.append(list(rawDataPrim))
                    f_raw_adc.append(list(adcData))
                    #print(count)

                except queue.Empty:
                    print("empty")
                    continue

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
                        c = sensID[refInd[0]]   # @@@ all references have to be on the same chassis
                        sensor_dict[c][0] = (sensID[refInd[0]][1], -bx_I, -by_I, None)
                        sensor_dict[c][1] = (sensID[refInd[1]][1], -bx_J, -by_J, None)
                        sensor_dict[c][2] = (sensID[refInd[2]][1], -bx_K, -by_K, None)

                        # print(sensor_dict)

                    # 3.1.1 | save compensation values onto compRef matrix

                    compRef = np.zeros([len(refInd),2])
                    compRef[0,0], compRef[0,1] = bx_I, by_I
                    compRef[1,0], compRef[1,1] = bx_J, by_J
                    compRef[2,0], compRef[2,1] = bx_K, by_K
                    f_compRef.append(compRef)

                # 3.2 | Primary sensors

                compPrim = np.zeros([nPrim, 3])
                gradPrim = np.zeros(nPrim)
                cc = 0
                for sens in range(nPrim):
                    # the sensor # within the chassis is the index into array of rotation matrices
                    c, s = sensID[primInd[sens]]
                    s -= 1  # make origin 0

                    bx, by, bz = getCompField_Prim(primRotMat[s], filt_f, 1)
                    compPrim[sens,:] = np.array([bx, by, bz]) # save compensation values
                    gradPrim[sens] = rawDataPrim[sens] - bz # compute 1st order gradiometer

                    if runDFC > 1 and (primInd[sens] in dfcInd):    # @@@ not working yet
                        tmp = (dictInd[sens], -bx, -by, None) # create tuple
                        sensor_dict[c][cc] = tmp # this is needed for the adjust_fields() call
                        cc +=1          # @@@ can use s here??

                f_compPrim.append(compPrim)
                f_gradPrim.append(gradPrim)

                if runDFC > 0:
                    # 4 | call adjust_fields()
                    print(sensor_dict)
                    service.adjust_fields(sensor_dict) # apply compensation field

                if flgControlC:
                    print('bye')
                    break

            # 5 | reset calls       # @@@ not working yet

            if runDFC > 0:
                # 5.1 | reset adjust_fields()
                if runDFC == 1:
                    cInd = [chassID[cI]]
                else:
                    cInd = chassID

                for c in cInd:
                    for i in range(len(sensor_dict[c])):
                        sensor_dict[c][i] = (sensor_dict[c][i][0], 0, 0, 0)

                service.adjust_fields(sensor_dict)
                print(sensor_dict)

            # 5.2 | stop getdata callback
            service.read_data()
            time.sleep(.01) # !!

            # 5.3 | stop clock
            stopped = time.time() - init
            print('tstop:' + str(stopped * 1000))

            # 5.4 | deactivate coil
            if coilID >= 0:
                print("turning coil off")
                coil.deactivate()
                coil.close()


        # 5.5 | Turn off all the sensors
        #print("acquire service")                   # it's already acquired
        #with FieldLineService(ip_list) as service:
        #   # sensors = service.load_sensors()
        #   # service.turn_off_sensors(sensors)
        #    service.stop_adc(0)
        #    #service.stop_adc(1)
        #    for s in sensID:                       # @@@
        #        f_coeffs.append(service.get_fields(chassID,s))

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
        f_coeffs = np.array(f_coeffs)

        print('saving data...')
        if nDfc != nPrim:
            suffix = '_'
            for dd in range(len(dfcInd)):
                suffix += str(dictInd[dfcInd[dd]]) + '-'
            suffix = suffix[:-1]
        else:
            suffix = ''
        sPath = './testData/test/' + prefix + sName + suffix
        chNs = chNames_Ref + chNames_Prim # add ADC name here


        np.save(sPath + '_rawRef', f_raw_Ref)
        np.save(sPath + '_rawPrim', f_raw_Prim)
        np.save(sPath + '_rawADC', f_raw_adc)
        np.save(sPath + '_filt', f_filt)
        np.save(sPath + '_compRef', f_compRef)
        np.save(sPath + '_compPrim', f_compPrim)
        np.save(sPath + '_gradPrim', f_gradPrim)
        np.save(sPath + '_coeffs', f_coeffs)
        np.save(sPath + '_refInd', refInd)
        np.save(sPath + '_dfcInd', dfcInd)
        np.save(sPath + '_primInd', primInd)
        np.save(sPath + '_chanNames', chNs)
        np.save(sPath + '_calib', calib)

        npy2fif(sPath, f_raw_adc, f_raw_Ref, f_raw_Prim, chNs, calib, f_compRef, f_compPrim, f_gradPrim)

        print('done.')

"""
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(threadName)s(%(process)d) %(message)s [%(filename)s:%(lineno)d]',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG if args.verbose else logging.ERROR,
        handlers=[stream_handler]
    )
"""

def parse_arguments():

    # Load a standard parser, add some extra parameters, and merge in the special parsers.

    p = Param()

    p.register("ipList", 'i', Str(), help="Comma separated list of IPs")
    p.register("restart", 'r', Bool(), help="Flag to restart sensors.", default=False)
    p.register("coarseZero", 'c', Bool(), help="Flag to coarse zero sensors.", default=False)
    p.register("fineZero", 'f', Bool(), help="Flag to fine zero sensors.", default=False)
    p.register("savingName", 's', Str(), arghelp="PATH", help="Path to save data.")
    p.register("runDFC", 'd', Int(), default=0, arghelp="N", help="0 (noDFC, default), 1 (refDFC), or 2 (primDFC).")
    p.register("coilID", 'C', Int(), default=-1, arghelp="N", help="Calibrator coil id. Default none (-1).")

    p.registryMerge(sens_p)     # sensor list parameters
    p.registryMerge(filt_p)     # filter parameters

    try:
        p = getParam(p)
    except Exception as e:
        print(e)
        sys.exit(1)

    p.enableLogging()
    p.logParam()

    return p

if __name__ == "__main__":

    # parse arguments
    p = parse_arguments()

    if not p.ipList:
        p.err("--ip is required")
    ip_list = p.ipList.split(',')

    flg_restart = p.restart
    flg_cz = p.coarseZero
    flg_fz = p.fineZero
    sName = p.savingName
    runDFC = p.runDFC
    coilID = p.coilID
    filter = p.FilterType
    refList = p.RefList
    primList = p.PrimList
    ADCList = p.ADCList

    nRef = len(refList)
    nPrim = len(primList)
    nADC = len(ADCList)

    # Convert ADCList to a list of just the chassis numbers

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
    elif filter[0] == 'n':
        filter_ref = nofilt(nRef)
    else:
        print(f"Unknown filter type {filter}.")
        sys.exit(1)

    print("Connecting to IPs:", ip_list)
    print("flg_restart", flg_restart)
    print("flg_cz", flg_cz)
    print("flg_fz", flg_fz)
    print("sName ", sName)
    print("runDFC", runDFC)

    main(ip_list, flg_restart, flg_cz, flg_fz, sName)

    print("exit")
    sys.exit(0)
