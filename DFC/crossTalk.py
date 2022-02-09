#! /usr/bin/env python

from fieldline_api.fieldline_service import FieldLineService
from fieldline_api.pycore.hardware_state import HardwareState
from fieldline_api.pycore.sensor import SensorInfo, ChannelInfo
from fieldline_api.fieldline_datatype import FieldLineWaveType

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
from npy2fif_raw import npy2fif_raw
from jig import getJigDef

#%%

def handler(signum,frame):
    global flgControlC
    flgControlC = 1  

signal.signal(signal.SIGINT, handler)

done = False
def call_done():
    global done
    done = True

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



#%%

primInd = range(15) # zero-based, EXCLUDING faulty sensor (if there is any)
faultySens = 13 # sensor 14 does not work
refInd = [15, 16, 17]	# need to get this from the jig.def file

closedLoop = 1 # 0: open loop (OL); 1: closed loop

# other variables
count = 0
g = 1e9  # to convert data into nanotesla
fs = 1000

def main(ip_list, flg_restart, flg_cz, flg_fz, amp, freq, coilType,td):
    
    # run restart | coarse | fine zeroing
    if flg_restart:
        restart_sensors(ip_list)
    if flg_cz:
        coarse_zero(ip_list)
    if flg_fz:
        fine_zero(ip_list)
        
    
    # load additional setup parameters
    global calib, chassID
    chassID, sensID, chNames, calib = getInfo(ip_list)
     
       
    print('loaded sensor IDs:', sensID)    
    print('channel names', chNames)
    print('len calib ', len(calib) , 'len sens ', len(list(primInd)+refInd))
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


        for ss in range(len(sensID)): # tuple containing chassis ID and sensor ID

            # initialize lists for saving data    
            f_raw_Ref = [] 
            f_raw_Prim = []   
            f_coeffs = [] 
            
            if sensID[ss][0]==0 or (sensID[ss][0] ==1 and sensID[ss][1]<=3):       
                print("Now running: chassis " + str(sensID[ss][0]) + ' | sensor ' + str(sensID[ss][1]))
                #print("press enter")
                #sys.stdin.read(1)
                rawDataRef = np.zeros(len(refInd))
                rawDataPrim = np.zeros(len(primInd))  
                global done
                done = False
                print(f"Doing fine zero")
                sensors = service.load_sensors()
                service.fine_zero_sensors(sensors,
                                            on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                                            on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                            on_completed=lambda: call_done())
                while not done:
                    time.sleep(0.01)

                global init
                init = time.time()
                started = time.time()-init
                print('tstart: ' + str(started*fs))

                
                if coilType == 0:
                    service.set_bx_wave(sensID[ss][0], sensID[ss][1], FieldLineWaveType.WAVE_SINE, freq, amp)
                    
                elif coilType ==1:
                    service.set_by_wave(sensID[ss][0], sensID[ss][1], FieldLineWaveType.WAVE_SINE, freq, amp)
                    
                else:
                    service.set_bz_wave(sensID[ss][0], sensID[ss][1], FieldLineWaveType.WAVE_SINE, freq, amp)



                service.read_data(getData)	# begin collecting data
                t0 = None
                while time.time()-init < td: # do bx/by/bz for td seconds
                      
                    # 1 | get raw data from queue
                    try:
                        data = q.get(timeout=0.5) 

                        for sens in range(len(refInd)):
                            rawDataRef[sens] = data['data_frames'][chNames_Ref[sens]]['data']*calib[refInd[sens]]*g

                        for sens in range(len(primInd)):
                            rawDataPrim[sens] = data['data_frames'][chNames_Prim[sens]]['data']*calib[primInd[sens]]*g

                        timestamp = data['timestamp']/25*1e3 # api uses a sampling rate of 25MHz
                        if t0 is None:
                            t0 = timestamp / 1000
                        print(timestamp / 1000 - t0)

                        f_raw_Ref.append(list(np.insert(rawDataRef,0,time.time()-init)))
                        f_raw_Prim.append(list(rawDataPrim))

                        #print(count)

                    except queue.Empty:
                        print("empty")
                        continue  
          
                print('turning coil ' + coils[coilType] + ' from chassis ' + str(sensID[ss][0]) + ' | sensor ' + str(sensID[ss][1]) + ' off...')

                if coilType == 0:               
                    service.set_bx_wave(sensID[ss][0], sensID[ss][1], FieldLineWaveType.WAVE_OFF, freq, amp)
                elif coilType ==1:
                    service.set_by_wave(sensID[ss][0], sensID[ss][1], FieldLineWaveType.WAVE_OFF, freq, amp)
                else: 
                    service.set_bz_wave(sensID[ss][0], sensID[ss][1], FieldLineWaveType.WAVE_OFF, freq, amp)

                # 5.2 | stop getdata callback  
                service.read_data()
                time.sleep(.01) # !!

                # 5.3 | stop clock
                stopped = time.time()-init
                print('tstop:' + str(stopped*1000))         
                
               
                f_coeffs.append(service.get_fields(sensID[ss][0],sensID[ss][1])) 
            

                # 6 | convert lists onto numpy arrays & save them
            
                f_raw_Ref = np.array(f_raw_Ref) 
                f_raw_Prim = np.array(f_raw_Prim)
                f_coeffs = np.array(f_coeffs)

                
                sPath = 'crossTalkData/chass' + str(sensID[ss][0]) + '_sens' + str(sensID[ss][1]) + '_coil' + coils[coilType]
       
                chNs = chNames_Ref + chNames_Prim
                npy2fif_raw(sPath, f_raw_Ref, f_raw_Prim, chNs, calib)

                np.save(sPath + '_rawRef', f_raw_Ref)
                np.save(sPath + '_rawPrim', f_raw_Prim)
                np.save(sPath + '_zeroCoeffs', f_coeffs)
           

                print('done.')

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Include debug-level logs.")
    parser.add_argument("-i", '--ip', type=lambda x: x.split(","), help="comma separated list of IPs", required=True)
    parser.add_argument("-r", '--restart', action='store_true', default=False, help="Flag to restart sensors.")
    parser.add_argument("-c", '--coarseZero', action='store_true', default=False, help="Flag to coarse zero sensors.")
    parser.add_argument("-f", '--fineZero', action='store_true', default=False, help="Flag to fine zero sensors.")
    parser.add_argument('-fr', '--freq', type=float, default=10, help="Frequency")
    parser.add_argument('-a', '--amp', type=float, default=1, help="Amplitude")
    parser.add_argument('-t', '--time', type=int, default=100, help="Time in seconds")
    parser.add_argument('-rt', '--rate', type=int, default=1000, help="Sampling rate")
    parser.add_argument('-co', '--coil', type=int, default=2, help = "coil to energize: 0=bx; 1=by;[2]=bz")
    parser.add_argument('--waveonly', action='store_true', default=False, help="Only update the wave")
    args = parser.parse_args()
    args.sync = True

    return args

if __name__ == "__main__":

    # parse arguments
    args = parse_arguments()
    
    ip_list = args.ip
    flg_restart = args.restart
    flg_cz = args.coarseZero
    flg_fz = args.fineZero
    freq = args.freq
    amp = args.amp
    td = args.time
    coilType = args.coil
    coils = ['bx','by', 'bz']

    print("Connecting to IPs:", ip_list)
    print("flg_restart", flg_restart)
    print("flg_cz", flg_cz)
    print("flg_fz", flg_fz)
    print("energizing coil", coils[coilType])
    
    main(ip_list, flg_restart, flg_cz, flg_fz, amp, freq, coilType, td)

    print("exit")    
    sys.exit(0)
