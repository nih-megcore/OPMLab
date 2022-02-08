#! /usr/bin/env python

from fieldline_api.fieldline_service import FieldLineService
from fieldline_api.pycore.hardware_state import HardwareState
from fieldline_api.pycore.sensor import SensorInfo, ChannelInfo

import logging
import threading
import argparse
import queue
import time
import sys
import string
import numpy as np
import signal
import copy
from numato import numato
from npy2fif import npy2fif
from jig import getJigDef

#%%

"""
Dynamic field compensation (dfc) for every incoming sample.
This process consists of:
1. Get sample (sample = data*calibration coefficient [in T])
2. Compute exponential moving average
3. Compute compensation fields using predefined 'rotation' matrices
4. Apply compensation fields
"""


def handler(signum,frame):
    global flgControlC
    flgControlC = 1  

signal.signal(signal.SIGINT, handler)

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

def getInfo(ip_list):    
    """
    this function grabs basic information from the setup:
    - chassis ID
    - channel names (without the open loop [:28]/closed loop [:50] indicator)
    - calibration values
    """
    print("[getInfo]")

    if closedLoop:
        suffix = ':50'
    else:
        suffix = ':28'

    ch_names = []
    calib = []
    sensID = []
    with FieldLineService(ip_list) as service:
        sensors = service.load_sensors()
        print(sensors)
        chassID = list(sensors.keys())

        for c in chassID:
            for s in sensors[c]:
                sensID.append((c, s))
                ch_names.append(service.hardware_state.get_sensor(c, s).name + suffix)

        for ch in ch_names:
            calib.append(service.get_calibration_value(ch)['calibration'])

    return chassID, sensID, ch_names, calib



def loadRotMat_RefSens():
    """
    load pre-computed rotation matrices for reference sensors (I,J,K)
    the I,J,K sensors are placed in the IJK coordinate system we need
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


def getCompField_Ref(R, mav, g):
    """
    compute compensation fields for transverse coils of reference sensors
    input parameters:
    - R: pre-loaded rotation matrix of ref sensors I,J,K
    - mav: moving average of measured reference fields
    - g: scaling factor to transform values to nT
    """

    measured_f = mav.T  # [3x1]
    compensat_f = g*(R.dot(measured_f))  # [3x1]
    bx = compensat_f[0]  # compensation to be applied on x coil
    by = compensat_f[1]  # compensation to be applied on y coil
    
    return bx,by



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

def getCompField_Prim(R, mav, g):
    """
    compute compensation fields for transverse coils of reference sensors
    input parameters:
    - R: pre-loaded rotation matrix of primary sensors
    - mav: moving average of measured reference fields
    - g: scaling factor to transform values to nT
    """

    measured_f = mav.T  # [3x1]
    compensat_f = g*(R.dot(measured_f))  # [3x1]
    bx = compensat_f[0]  # compensation to be applied on x coil
    by = compensat_f[1]  # compensation to be applied on y coil
    bz = compensat_f[2]  # compensation to be applied on z coil
    return bx,by, bz


def ema_ref(data, a):
    """
    compute exponential moving average
    input parameters:
    - data: newest sample
    - a: time decay
    """
    global mav
    mav = a*mav + (1-a)*data
    #print(mav)


#%%

primInd = range(15) # zero-based, EXCLUDING faulty sensor (if there is any)
faultySens = 13 # sensor 14 does not work
refInd = [15, 16, 17]	# need to get this from the jig.def file
dfcInd = [1,3,4,6,9,11,12,13]#range(15) 

coilID = 0 # -1 : don't energize coil; 0-36, energize coil corresponding to that number
tCoilStart = 0 # in seconds

#runDFC = 0 # 0: don't run DFC; 1: run for Refs only; 2: run for primary and refs sensors
closedLoop = 1 # 0: open loop (OL); 1: closed loop

# define dynamic field compensation parameters
td = 300 # duration of applied compensation segment [in seconds]
nResets = 0 # defines the # of repetitions of a fine_zero-dfc block. If 0, the block is repeated once.

# define moving average parameters
tau = 0.01  # 10 ms; moving average 
fs = 1000 # sampling rate
a = np.e**(-1/(fs*tau)) # time decay

# get dictionary index for adjust_fields()
sArr = range(1,17) # this is the default sensor id per chassis. It is one-based
if faultySens:
    dictInd = np.setdiff1d(sArr, faultySens+1)
else:
    dictInd = sArr
try:
    if len(dictInd)!= len(primInd):
        raise DimError
except DimError as err:
    print(err)

# other variables
count = 0
mav = np.zeros([1,len(refInd)])
g = 1e9  # to convert data into nanotesla
flgControlC = False
onceCoil = False

def main(ip_list, flg_restart, flg_cz, flg_fz, sName):
    
    global sensor_dict 
    if coilID >= 0: 
        global coil
        coil = numato() # initialize class to energize coil
        coil.setOutputMode()
        coil.command('gpio writeall 00') # make sure coils are off
        global onceCoil
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
    
    if faultySens:
        print(primRotMat.shape)
        primInd2 = range(0,16)
        indx = list(np.setdiff1d(primInd2,np.array(faultySens)))
        print(indx)
        primRotMat = primRotMat[indx,:,:] 
        print(primRotMat.shape)
    
    # load additional setup parameters
    global calib, chassID
    chassID, sensID, chNames, calib = getInfo(ip_list)

    # sensors we will use
    sensors = {}
    for c in chassID:
        sensors[c] = []
    for i in refInd:
        c, s = sensID[i]
        sensors[c].append(s)
    for i in primInd:
        c, s = sensID[i]
        sensors[c].append(s)

    # define sensor_dict for adjust_fields()
    if runDFC ==1:
        cInd = [chassID[1]]
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
    f_filt =[] 
    f_compRef = []    
    f_compPrim = []
    f_gradPrim = []     
    f_coeffs = [] 
    
    print("acquire service")
    with FieldLineService(ip_list) as service:
        q = queue.Queue(10) # queue is needed to access bz data outside the getData callback
        
        def getData(data):
            """
            this function is a callback to read the data structure in the stream
            the data is saved on a queue that can be accessed outside of this function
            the variable count is used for debugging purposes
            """
            global count
            count += 1
            q.put(data)

        print("Press Enter")
        sys.stdin.read(1)

        service.start_adc(0)

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

            global mav
            mav = np.zeros([1,len(refInd)])

            print("setting dfc")

            global init
            init = time.time()
            started = time.time()-init
            print('tstart: ' + str(started*fs))

            service.read_data(getData)	# begin collecting data
            #time.sleep(.001)

            rawDataRef = np.zeros(len(refInd))
            rawDataPrim = np.zeros(len(primInd))           

            t0 = None
            while time.time()-init < td: # do dfc for td seconds

                if count >= int(tCoilStart*fs) and onceCoil:
                    if coilID >= 0:                                   
                        # energize coil
                        s = 'gpio writeall ' + str(hex(64+coilID)[2:])
                        coil.command(s) 
                        onceCoil = False

                # 1 | get raw data from queue
                try:
                    data = q.get(timeout=0.5) 

                    for sens in range(len(refInd)):
                        rawDataRef[sens] = data['data_frames'][chNames_Ref[sens]]['data']*calib[refInd[sens]]*g

                    for sens in range(len(primInd)):
                        rawDataPrim[sens] = data['data_frames'][chNames_Prim[sens]]['data']*calib[primInd[sens]]*g
                   
                    adcData = data['data_frames']['00:00:0']['data']*2.980232238769531e-07

                    timestamp = data['timestamp']/25*1e3 # api uses a sampling rate of 25MHz
                    if t0 is None:
                        t0 = timestamp / 1000
                    print(timestamp / 1000 - t0)

                    f_raw_Ref.append(list(np.insert(rawDataRef,0,time.time()-init)))
                    f_raw_Prim.append(list(rawDataPrim))
                    f_raw_adc.append(adcData)

                    #print(count)

                except queue.Empty:
                    print("empty")
                    continue

                # 2 | compute moving average of reference sensors

                if refInd:        
                    ema_ref(rawDataRef, a)  # the output of this is mav
                    f_filt.append(mav[0]) 
            
                    # 3 | compute & save compensation fields
                
                    # 3.1 | Ref sensors
                    bx_I, by_I = getCompField_Ref(rot_RefI, mav[0], 1)
                    bx_J, by_J = getCompField_Ref(rot_RefJ, mav[0], 1)
                    bx_K, by_K = getCompField_Ref(rot_RefK, mav[0], 1)

                    if runDFC > 0:     # @@@ all references have to be on the same chassis
                        sensor_dict[chassID[1]][0] = (sensID[refInd[0]][1], -bx_I, -by_I, None)
                        sensor_dict[chassID[1]][1] = (sensID[refInd[1]][1], -bx_J, -by_J, None)
                        sensor_dict[chassID[1]][2] = (sensID[refInd[2]][1], -bx_K, -by_K, None)
                       # print(sensor_dict)

                    # 3.1.1 | save compensation values onto compRef matrix
                
                    compRef = np.zeros([len(refInd),2])
                    compRef[0,0], compRef[0,1] = bx_I, by_I
                    compRef[1,0], compRef[1,1] = bx_J, by_J
                    compRef[2,0], compRef[2,1] = bx_K, by_K                  
                    f_compRef.append(compRef)
            
                # 3.2 | Primary sensors

                compPrim = np.zeros([len(primInd),3])
                gradPrim = np.zeros(len(primInd))
                cc = 0
                for sens in range(len(primInd)):

                    bx, by, bz = getCompField_Prim(primRotMat[primInd[sens]], mav[0], 1)
                    compPrim[sens,:] = np.array([bx, by, bz]) # save compensation values
                    gradPrim[sens] = rawDataPrim[sens] - bz # compute 1st order gradiometer

                    if runDFC > 1 and (primInd[sens] in dfcInd):
                        tmp = (dictInd[sens],-bx,-by, None) # create tuple
                        sensor_dict[chassID[0]][cc] = tmp # this is needed for the adjust_fields() call                  
                        cc +=1
                      
                f_compPrim.append(compPrim)
                f_gradPrim.append(gradPrim)

                if runDFC > 0:
                    # 4 | call adjust_fields()               
                    service.adjust_fields(sensor_dict) # apply compensation field    
                   
                if flgControlC:
                    print('bye')
                    break       

            # 5 | reset calls
            
            if runDFC > 0:
                # 5.1 | reset adjust_fields()
                if runDFC ==1:
                    cInd = [chassID[1]]
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
            stopped = time.time()-init
            print('tstop:' + str(stopped*1000))         
            
            # 5.4 | deactivate coil
            if coilID >= 0:
                print("turning coil off")
                coil.command('gpio writeall 00')
                coil.close()
            

        # 5.5 | Turn off all the sensors
        print("acquire service")
        with FieldLineService(ip_list) as service:
           # sensors = service.load_sensors()
           # service.turn_off_sensors(sensors)
            service.stop_adc(0)
            for s in sensID:
                f_coeffs.append(service.get_fields(chassID,s)) 

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
        if len(dfcInd) != len(primInd):
            suffix = '_'
            for dd in range(len(dfcInd)):
                suffix += str(dictInd[dfcInd[dd]]) + '-'
            suffix = suffix[:-1]           
        else:
            suffix = ''
        sPath = 'testData/' + prefix + sName + suffix
        chNs = chNames_Ref + chNames_Prim # add ADC name here
        npy2fif(sPath, f_raw_adc, f_raw_Ref, f_raw_Prim, chNs, calib)

        #np.save(sPath + '_rawRef', f_raw_Ref)
        #np.save(sPath + '_rawPrim', f_raw_Prim)
        #np.save(sPath + '_rawADC', f_raw_adc)
        np.save(sPath + '_filt', f_filt)
        np.save(sPath + '_compRef', f_compRef)
        np.save(sPath + '_compPrim', f_compPrim)
        np.save(sPath + '_gradPrim', f_gradPrim)
        np.save(sPath + '_coeffs', f_coeffs)
        np.save(sPath + '_refInd', refInd)
        np.save(sPath + '_dfcInd', dfcInd)
        np.save(sPath + '_primInd', primInd)
        np.save(sPath + '_chanNames', chNames)
        np.save(sPath + '_calib', calib)

        print('done.')

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Include debug-level logs.")
    parser.add_argument("-i", '--ip', type=lambda x: x.split(","), help="comma separated list of IPs", required=True)
    parser.add_argument("-r", '--restart', action='store_true', default=False, help="Flag to restart sensors.")
    parser.add_argument("-c", '--coarseZero', action='store_true', default=False, help="Flag to coarse zero sensors.")
    parser.add_argument("-f", '--fineZero', action='store_true', default=False, help="Flag to fine zero sensors.")
    parser.add_argument("-s", '--savingName', type=str, help="Path to save data.")
    parser.add_argument("-d", '--runDFC', type=int, default=0, help="0 (noDFC), 1 (refDFC), or 2 (primDFC).")
    args = parser.parse_args()

    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(threadName)s(%(process)d) %(message)s [%(filename)s:%(lineno)d]',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG if args.verbose else logging.ERROR,
        handlers=[stream_handler]
    )

    return args

if __name__ == "__main__":

    # parse arguments
    args = parse_arguments()
    
    ip_list = args.ip
    flg_restart = args.restart
    flg_cz = args.coarseZero
    flg_fz = args.fineZero
    sName = args.savingName
    runDFC = args.runDFC

    if runDFC == 0 :
        prefix = 'noDFC_'
    elif runDFC == 1 :
        prefix = 'refDFC_'
    else:
        prefix = 'primDFC_'

    print("Connecting to IPs:", ip_list)
    print("flg_restart", flg_restart)
    print("flg_cz", flg_cz)
    print("flg_fz", flg_fz)
    print("sName ", sName)
    print("rundfc", runDFC)

    main(ip_list, flg_restart, flg_cz, flg_fz, sName)

    print("exit")    
    sys.exit(0)
