from fieldline_api.fieldline_service import FieldLineService

import logging
import argparse
import queue
import time
import sys
import numpy as np
from numato import numato

#%%


def parse_arguments():

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose',
                        action='store_true', default=False,
                        help="Include debug-level logs.")
    parser.add_argument("-i", '--ip',
                        type=lambda x: x.split(","),
                        help="comma separated list of IPs",
                        required=True)
    #parser.add_argument("-r", '--restart',
    #                    action='store_true', default=True,
    #                    help="Flag to restart sensors.")
    #parser.add_argument("-c", '--coarseZero',
    #                    action='store_true', default=True,
    #                    help="Flag to coarse zero sensors.")
    #parser.add_argument("-f", '--fineZero',
    #                    action='store_true', default=True,
    #                    help="Flag to fine zero sensors.")
    #parser.add_argument("-s", '--savingPath',
    #                    "--string", type=str,
    #                    help="Path to save data.")
    args = parser.parse_args()

    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(threadName)s(%(process)d) %(message)s [%(filename)s:%(lineno)d]',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG if args.verbose else logging.ERROR,
        handlers=[stream_handler]
    )

    return args


def restart_sensors(ip_list):
    global done
    try:
        with FieldLineService(ip_list) as service:
            done = False
            # Get dict of all the sensors
            sensors = service.load_sensors()
            sensors = {0: [1,5,9]}
            print(f"Got sensors: {sensors}")
            # Make sure closed loop is set
            service.set_closed_loop(True)
            print("Doing sensor restart")
            # Do the restart
            service.restart_sensors(sensors, on_next=lambda c_id,
                                    s_id: print(f'sensor {c_id}:{s_id} finished restart'),
                                    on_error=lambda c_id, s_id,
                                    err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                    on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))


def coarse_zero(ip_list):
    global done
    try:
        with FieldLineService(ip_list) as service:
                done = False
                sensors = service.load_sensors()
                sensors = {0: [1,5,9]}
                print(f"Got sensors: {sensors}")
                time.sleep(2)
                print("Doing coarse zero")
                service.coarse_zero_sensors(sensors, on_next=lambda c_id,
                                            s_id: print(f'sensor {c_id}:{s_id} finished coarse zero'),
                                            on_error=lambda c_id, s_id,
                                            err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
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
            sensors = {0: [1,5,9]}
            print(f"Got sensors: {sensors}")
            print("Doing fine zero")
            service.fine_zero_sensors(sensors, on_next=lambda c_id,
                                        s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                                        on_error=lambda c_id, s_id,
                                        err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                        on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)
    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))


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


def ema(data, a):
    """
    compute exponential moving average
    input parameters:
    - data: newest sample
    - a: time decay
    """
    global mav
    mav = a*mav + (1-a)*data
    #print(mav)

count = 0

mav = np.zeros([1,3])

def main(ip_list, flg_restart, flg_cz, flg_fz, a, td, nResets, sPath):

    g = 1e9  # to convert data into nanotesla
    coil = numato()
    runDFC = True
    rot_RefI, rot_RefJ, rot_RefK = loadRotMat_RefSens()  # load rot matrices
    
    if flg_restart:
        restart_sensors(ip_list)
    if flg_cz:
        coarse_zero(ip_list)
    if flg_fz:
        fine_zero(ip_list)
    

    if runDFC:
        
        f_raw = [] # open(sPath + "_raw.txt","w")
        f_filt =[] # open(sPath + "_filt.txt","w")
        f_comp = [] #open(sPath + "_compFields.txt","w")        
        f_coeffs = [] # open(sPath + "_getFields.txt","w")

        with FieldLineService(ip_list) as service:
            
           # print("calib ", service.get_calibration_value('00:01:50'))
            # fine zero seems to be necessary before calling this function
            calib = [service.get_calibration_value('00:01:50')['calibration'],
                     service.get_calibration_value('00:05:50')['calibration'],
                     service.get_calibration_value('00:09:50')['calibration']]
            
           # service.start_adc(0)
            
            q = queue.Queue(10)
            
            def dfc(data):

                """
                Dynamic field compensation (dfc) for every incoming sample.
                This process consists of:
                1. Get sample (sample = data*calibration coefficient [in T])
                2. Compute exponential moving average
                3. Compute compensation fields using predefined 'rotation' matrices
                4. Apply compensation fields
                """
                global count
#                print(f"[dfc {count}]")
                count += 1
                #print(data)


                # 1 | get raw data
                """
                rawData = np.array([data['data_frames']['00:00:0']['data'],
                                    data['data_frames']['00:01:50']['data']*calib[0],
                                    data['data_frames']['00:05:50']['data']*calib[1],
                                    data['data_frames']['00:09:50']['data']*calib[2]])  # in Tesla 
                
                timestamp = data['timestamp']/25*1e3 # api uses a sampling rate of 25MHz
                """
                q.put(data)
                #q.put((rawData,timestamp))
                

            global done
            for n in range(nResets+1): # this block does fine zeroing before the dfc is started
            
                done = False
                sensors = service.load_sensors()
                print(f"Doing fine zero {n}")
                service.fine_zero_sensors(sensors, on_next=lambda c_id,
                                            s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                                            on_error=lambda c_id, s_id,
                                            err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                                            on_completed=lambda: call_done())
                while not done:
                    time.sleep(0.5)


                # save zero coeffs every time we call fine_zero
                f_I = service.get_fields(0,1)
                f_J = service.get_fields(0,5)
                f_K = service.get_fields(0,9)
                
                coeffs = [f_I, f_J, f_K]
                f_coeffs.append(coeffs)
              
                service.start_adc(0)  
                # add user input to start recording

                print("Press Enter")
                sys.stdin.read(1)
                                
                # energize coil
                coilID = 0
                coil.setOutputMode()
                s = 'gpio writeall ' + str(hex(64)[2:])
                coil.command(s)
                
                global mav                
                mav = np.zeros([1,3])
                print("setting dfc")
                        
                if n == 0 : 
                    init = time.time()
                    started = time.time()-init
                    print('tstart: ' + str(started*1000))
                
                service.read_data(dfc)
                
                while time.time()-init < td: # do dfc for td seconds

                    try:                    
                        data = q.get(timeout=0.5)  
                        rawData = np.array([data['data_frames']['00:00:0']['data'],
                                    data['data_frames']['00:01:50']['data']*calib[0]*g,
                                    data['data_frames']['00:05:50']['data']*calib[1]*g,
                                    data['data_frames']['00:09:50']['data']*calib[2]*g])  # in nanoTesla 

                        timestamp = data['timestamp']/25*1e3 # api uses a sampling rate of 25MHz

                        #print(count, rawData)
                        f_raw.append(list(np.insert(rawData,0,time.time()-init)))
                        
                    except queue.Empty:
                        print("empty")
                        continue

                    # 2 | compute moving average of data
                    ema(rawData[1:], a)  # the output of this is mav
                    f_filt.append(mav[0]) # this is necessary to make a copy of the object
                    #print(f_filt)
                    
                    
                    # 3 | compute compensation fields
                    bx_I, by_I = getCompField_Ref(rot_RefI, mav[0], 1)
                    bx_J, by_J = getCompField_Ref(rot_RefJ, mav[0], 1)
                    bx_K, by_K = getCompField_Ref(rot_RefK, mav[0], 1)
                    
                    tmp = [bx_I, by_I, bx_J, by_J, bx_K, by_K]
                    f_comp.append(tmp)

                    
                    # 4 | apply compensation fields
                    sensor_dict = {0: [(1, -bx_I, -by_I, None),
                                       (5, -bx_J, -by_J, None),
                                       (9, -bx_K, -by_K, None)]}
                    
                    #sensor_dict = {0:[(1,None,None,None)]}
    
                    service.adjust_fields(sensor_dict) # apply compensation field    
                              
                
                sensor_dict = {0: [(1, 0, 0, 0),
                                   (5, 0, 0, 0),
                                   (9, 0, 0, 0)]}

                service.adjust_fields(sensor_dict)    
                service.read_data()
                stopped = time.time()-init
                print('tstop:' + str(stopped*1000))         
                
                
                s = 'gpio writeall 00'
                coil.command(s)
                coil.close()
                
            f_raw = np.array(f_raw)    
            f_filt = np.array(f_filt)
            print(f_filt)
            f_comp = np.array(f_comp)
            f_coeffs = np.array(f_coeffs)
            np.save(sPath + '_raw', f_raw)
            np.save(sPath + '_filt', f_filt)
            np.save(sPath + '_comp', f_comp)
            np.save(sPath + '_coeffs', f_coeffs)

                
            # Turn off all the sensors
            with FieldLineService(ip_list) as service:
#                sensors = service.load_sensors()
#                service.turn_off_sensors(sensors)
                service.stop_adc(0)
            

if __name__ == "__main__":

    # parse arguments
    args = parse_arguments()

    ip_list = args.ip
    flg_restart = 0 #args.restart
    flg_cz = 0 #args.coarseZero
    flg_fz = 1 #args.fineZero
    sPath = '/home/holroydt/opm/CADFC/testData/withDFC_chassis2_20220125_27Hz_2V'# args.savingPath

    print(f"Connecting to IPs: {ip_list}")
    print("flg_restart " + str(flg_restart))
    print("flg_cz " + str(flg_cz))
    print("flg_fz " + str(flg_fz))

    # define moving average parameters
    tau = 0.01  # 10 ms
    fs = 1000 # sampling rate
    a = np.e**(-1/(fs*tau)) # time decay

    # define dynamic field compensation parameters
    td = 300 # duration of applied compensation segment [in seconds]
    nResets = 0 # defines the # of repetitions of a fine_zero-dfc block. If 0, the block is repeated once.

    done = False
    def call_done():
        global done
        done = True


    main(ip_list, flg_restart, flg_cz, flg_fz, a, td, nResets, sPath)



