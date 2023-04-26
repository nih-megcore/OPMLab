#! /usr/bin/env python

import sys
import logging
import threading
import time
import numpy as np
import signal

from service import FLService # FieldLine api needed for this
from numato import numato # class used to control the test dipole coil
#from sensorMapping import * # to map channel names <---> coordinates & orientations 
#from prepForDFC import *
from npy2fif_7x8 import * # to save in mne format
from param import * # input parameter parsing
from filters import * # filter ref sensors 
#from filters import getFilter
from sensors import *
from presets import * # this allows to select which sensors are selected for DFC 
from io_dfc import *

import tensorly as tl # use sensors to compute compensation values
from collections import deque
from constants import * 

import gc # garbage collector
if gc.isenabled():
    gc.disable()
    
    
#%%

#class struct:
#    pass

# Handle ^C

flgControlC = False
def handler(signum, frame):
    global flgControlC
    flgControlC = 1

signal.signal(signal.SIGINT, handler)


#%%

tCoilStart = 0 # control when to energize coil after fine-zero has been completed (in seconds)
count  = -1
done = False

def main(p, logger): #@@ use logging module 


    #### ----------------------------------------------------------- ####
    #                      INITIALIZE QUEUE                             # 
    #### ----------------------------------------------------------- ####
    
    
    # queue is needed to access bz data outside the getData callback

    q = deque()
    event = threading.Event()

    def getData(data):

        """ 
        This function is a callback to read the data structure in the stream.
        The data are place in a queue which can be accessed outside of this function.
        """

        global count

        count += 1
        q.append(data)
        event.set()

    
    #### ----------------------------------------------------------- ####
    #                      PREPARE FOR DFC                              # 
    #### ----------------------------------------------------------- ####

       
    # initialize class instances
    
    s_sens = SensorManager()
    s_sens.logger = logger # give logging properties to s_sens    
    
    s_data = struct()        
    
    # init the test coil
    
    onceCoil = False
    if p.coilID >= 0:
        coil = numato()     # initialize class to energize coil
        coil.deactivate()   # make sure all coils are off
        onceCoil = True

    # Get FieldLine service
    
    service = FLService(p.ip_list)
      
    # Get sensor index/name/calib information
     
    s_sens, service = s_sens.prepareForDFC(service, s_data, p)
    
    # set up filter params
    
    filter_ref = getFilter(s_sens, p.FilterType)        

    # load cell positions, coil orientations
    
    cellCoords, rotMat = extractArrayInfo()    
    
    # extract variables from s_sens and p for efficient DFC computation

    chassID, chNames_Ref, chNames_Prim, ADCnames, calib, selCSs, selInArray = s_sens.extractFromStruct()
    td = p.duration
    runDFC = p.runDFC

    # ask user to press enter to start doing fine zero + collecting data
    
    print("Press Enter")
    sys.stdin.read(1)

    #### ----------------------------------------------------------- ####
    #                            MAIN LOOP                              # 
    #### ----------------------------------------------------------- ####

    # Get ready to energize the coil as quickly as possible after fine zero is complete

    if p.coilID >= 0:
        coil.preactivate(p.coilID)

    # Initialize filter

    filter_ref.restart()
    
    # preallocate memory
    
    arrLen = int(td*fs) + 50 # to account for len(queue)>1 in the last iteration of loop
    t_arr = np.empty((arrLen,1))
    t_DFC = np.ones((arrLen,1)) * -1

    nADC = len(s_sens.ADCchas)
    nRef = len(chNames_Ref)
    nPrim = len(chNames_Prim)

    rawDataRef = np.empty((arrLen, nRef))
    rawDataPrim = np.empty((arrLen, nPrim))
    rawDataADC = np.empty((arrLen, nADC))
    
    # define counters
    
    t0 = None
    sDropped = 0
    sampleCount, dfcC = -1, -1
    
    # start streaming adc
    
    for c in s_sens.ADCchas:
        service.start_adc(c)

    # Do fine zero
    
    logger.info("Doing fine zero")
    tfz0 = time.perf_counter_ns()
    service.fineZero(s_sens.sdict)
    fztime = time.perf_counter_ns() - tfz0

    # Begin streaming data
    
    service.read_data(getData)

    # actual while loop
    logger.info('Start experiment')
    
    while sampleCount < (td * fs): 
                    
        # energize calibration coil
        
        if onceCoil and p.coilID >=0:
            coil.go()
            onceCoil = False
            
        # grab data from queue until queue is empty
                      
        event.wait()
        tstamps_ = [] # store all time stamps in queue  
        updateDrops = 1
                                          
        while len(q)>0:
                
            sampleCount += 1
            
            # remove oldest item in queue
             
            data = q.popleft()
            
            # show data_frame dictionary keys for first iteration
            if sampleCount == 0:
                logger.info(f"keys in dataframe\n{list(data['data_frames'].keys())}")     
            
            # keep track of how many items are in the queue
            
            if len(q) > 0 and updateDrops: 
                sDropped += len(q)
                updateDrops = 0

            # read data from queue                    
                
            for sens in range(nRef):
                rawDataRef[sampleCount,sens] = data['data_frames'][chNames_Ref[sens]]['data']*calib*g # in nT

            for sens in range(nPrim):
                rawDataPrim[sampleCount,sens] = data['data_frames'][chNames_Prim[sens]]['data']*calib*g # in nT

            for i_adc in range(nADC):
                rawDataADC[sampleCount,i_adc] = data['data_frames'][ADCnames[i_adc]]['data']*calib_ADC
            
            # get timestamp & store it   
            
            timestamp = data['timestamp']/25*1e3  #api uses a sampling rate of 25MHz
            
            if t0 is None:
                t0 = timestamp / fs
                init = time.perf_counter_ns()
            
            tstamps_.append(timestamp/fs - t0) # for printing
            
            t_arr[sampleCount] = (timestamp/fs) - t0
            
            # filter every sample measured by the reference sensors if selected
            
            if runDFC > 0:
                ref_filt = filter_ref(rawDataRef[sampleCount,:])
        
        # Update DFC counter 
        
        dfcC +=1
        t_DFC[dfcC] = timestamp/fs -t0
                                        
        # clear event lock so that new items can be placed in the queue 
        
        event.clear()
        
        # print elapsed time
            
        if sampleCount %100 == 0:                
            print(sampleCount, tstamps_, t_DFC[dfcC]) 
                                                  
        # do DFC
                
        if runDFC > 0:
         
            # compute compensation matrix using tensor multiplication
            
            compM_ = tl.tenalg.mode_dot(rotMat[:,:, selInArray], ref_filt, mode=1).T
                
            # add compensation fields to correct CAPE effects
            # 1. build a dictionary of the form {chassisID: [(sensorID, x field, y field, z field),...]}
                 # no z field compensation is done because the code assumes operation mode is set to closed loop  
            
            sensor_dict = {i: [(cs[1], -comp[0], -comp[1], None) for cs, comp in zip(selCSs,compM_) if cs[0]==i] for i in chassID}
            
            # call API function to change the fields
            
            service.adjust_fields(sensor_dict)
            
        # ^C to quit the program
                        
        if flgControlC:
            logger.info("Experiment aborted.")
            break

    # Out of the while loop.


    #### ----------------------------------------------------------- ####
    #                       RESET/STOP CALLS                            # 
    #### ----------------------------------------------------------- ####

    # Reset adjust_fields

    if s_sens.runDFC > 0:
    
        sensor_dict = {i: [(cs[1], 0, 0, 0) for cs in selCSs if cs[0]==i] for i in chassID}
        service.adjust_fields(sensor_dict)
        
    # stop getdata callback
    
    logger.info("stopping data stream.")
    service.read_data()
    
    for c in s_sens.ADCchas:
        service.stop_adc(c)

    # Print total elapsed time & DFC stats
    
    endT = (time.perf_counter_ns()-init)
    
    logger.info("------------------------------------------------------------\n")
    logger.info(f"elapsed time (ms): {endT*1e-6}")
    logger.info(f"elapsed time according to FL (ms): {timestamp / 1000 - t0}")
    logger.info(f"dropped samples: {sDropped} out of {sampleCount} samples. Proportion %{100*sDropped/sampleCount}")
    logger.info("------------------------------------------------------------\n")
    
    # deactivate coil

    if p.coilID >= 0:
        s_sens.info("turning coil off")
        coil.deactivate()
        coil.close()
        onceCoil = True
    
    # Get fine zero values
    
    fzCoeffs = service.getCoeffs(s_sens.sdict)
    
    
    #### ----------------------------------------------------------- ####
    #                         SAVE VARIABLES                            # 
    #### ----------------------------------------------------------- ####

    # recorded data-related instance
    
    s_data.rawDataADC = rawDataADC[:int(td*fs)+1,:]
    s_data.rawDataPrim = rawDataPrim[:int(td*fs)+1,:]
    s_data.rawDataRef = rawDataRef[:int(td*fs)+1,:]
    s_data.tArray = t_arr[:int(td*fs)+1]
    s_data.FZ_coeffs = fzCoeffs
    s_data.FZ_time = fztime
    if s_sens.runDFC > 0:
        s_data.sDropped = sDropped
        s_data.t_DFC = t_DFC[:int(td*fs)+1]
        
    # array geometry-related instance

    s_geom = struct()
    s_geom.rotMat = rotMat
    s_geom.cell_coords = cellCoords
    
    # save variables
    
    logger.info("\nsaving raw data to .pkl files...")
   
    savePickle(s_data, p.sPath +  "_data.pkl")
    savePickle(s_sens, p.sPath +  "_sens.pkl")
    savePickle(s_geom, p.sPath +  "_geom.pkl")

    logger.info("done.")

    #### ----------------------------------------------------------- ####
    #                         CONVERT TO .FIF                           # 
    #### ----------------------------------------------------------- ####

    logger.info("\nsaving raw data to .fif file...") 
    npy2fif(s_data, s_sens, s_geom, filter_ref, p.sPath)
    logger.info("done.") 
    
       
                
    
if __name__ == "__main__":

    # Load a standard parser, add some extra parameters, and merge in the special parsers.

    p = Param()

    p.register("ipList", 'i', Str(), help = "Comma separated list of IPs")
    p.register("restart", 'r', Bool(), help = "Flag to restart sensors.", default=False)
    p.register("coarseZero", 'c', Bool(), help = "Flag to coarse zero sensors.", default=False)
    p.register("fineZero", 'f', Bool(), help = "Flag to fine zero sensors.", default=False)
    p.register("saveName", 's', Str(), arghelp ="NAME", help = "prefix name to save data.")
    p.register("savePath", None, Dirname(create = True), arghelp = "DIR", help = "Path to save data.")
    p.register("runDFC", 'd', Int(), default = 0, arghelp = "N", help = "0 (noDFC, default), 1 (refDFC), or 2 (primDFC).")
    p.register("coilID", 'C', Int(), default = -1, arghelp = "N", help = "Calibrator coil id. Default none (-1).")
    p.register("duration", 't', Float(), default = 0, arghelp = "DUR", help = "Length of recording in seconds.")
    p.register("closedLoop", None, Bool(), default = True, help = "Whether to use closed loop, default true.")

   
    help_preset = "use presets for channel selection.\n0 = don't use presets.\n1 = DFC to all available channels in array\n2 = DFC in checkerboard fashion in grid\n"
   
    p.register("presets", 'p', Int(), default = 0, help = help_preset) # @@@ this message is not complete
    p.registryMerge(sens_p)     # sensor list parameters 
    p.registryMerge(filt_p)     # filter parameters

    # Get all the parameters from the command line, environment, and parameter files.

    try:
        p = getParam(p)
    except Exception as e:
        print(e)
        sys.exit(0)
    
    # Sanity checks

    if not p.ipList:
        p.err("--ip is required")
    p.ip_list = p.ipList.split(',')

    if not p.saveName:
        p.saveName = 'test'
        
    p.prefix = 'noDFC_' if p.runDFC == 0 else 'refDFC_' if p.runDFC == 1 else 'primDFC_'
    
    # Check if filename already exists
    
    p.sPath = f"{p.savePath}/{p.prefix}{p.saveName}"
    p = p.checkSavingPath()
    
    # initialize logger with correct saving file name
    
    logger = configure_logging(p, mode='a')
      
    # Convert ADCList to a list of just the chassis numbers.
    
    print(f"\nADCList {p.ADCList}")
    
    # get selected DFC list
    
    if p.runDFC >0 and p.presets > 0:
        print(f"\nDFC mode: {p.runDFC}")
        p.dfcList = createPreset(p, logger) 
        print(f"\nDFC list: {p.dfcList}")
    elif p.runDFC == 0:
        print(f"\n NO DFC will be applied")
        
    # use print instead of logger since this info is already saved in a .txt file
    
    print(f"\nConnecting to IPs: {p.ip_list}")
    print(f"\nflg_restart {p.restart}")
    print(f"flg_cz {p.coarseZero}")
    print(f"flg_fz {p.fineZero}")
    print(f"\nexperiment duration set to : {p.duration} seconds")

    
    # Let user know if filename was modified
           
    if p.nameEd:
        logger.info(f"\nsaveName in .param file already existed in directory.\nsaveName was changed to: {p.sPath}")
    else: 
        logger.info(f"\nsPath: {p.sPath}")
    
    # run DFC

    main(p,logger)
    
    logger.info("exit")
    sys.exit(0)