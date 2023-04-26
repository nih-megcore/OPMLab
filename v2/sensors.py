"""This module contains functions for dealing with groups of sensors,
and using parameter files for specifying such groups."""

import time
from param import Param, propObj, Filename
import logging
import pandas as pd
import numpy as np
import sys
import os

# get directory from which DFC code is running

current_path = os.path.split(os.path.realpath(__file__))[0]
 
# Create a custom property object to parse sensor groups.

# A sensor is specified by a chassis number CC and a sensor number SS
# with CC:SS. A group of sensors is a comma or space separated list.
# Internally a sensor group is a list of tuples, [(CC, SS), ...]

class SList(propObj):
    """Store a list of sensors. This can be specified multiple times.
    The syntax CC:* is allowed, and expands to all 16 sensors."""

    def _set(self, p, val, cmdLine=False):
        slist = []
        l = self._get(p)    # see if already set
        if l:
            slist = l
        
        #print(slist)
        # make a new list with no commas
        vals = []
        for v in val:
            l = v.split(',')
            for name in l:
                name = name.strip()
                if len(name) == 0:  # val might have "00:01, 00:02, ..."
                    continue
                vals.append(name)

        n = 0
        ok = True
        for v in vals:
            try:
                c, s = v.split(':')
                c = int(c)
                if s == '*':
                    s = range(1, 17)
                    slist.extend([(c, x) for x in s])
                else:
                    s = int(s)
                    t = (c, s)
                    if t not in slist:  # ignore dups
                        slist.append(t)
            except:
                # if we're on the command line, an error means stop processing
                if not cmdLine:
                    raise ValueError(f"{self._name}: invalid sensor name '{name}'")
                ok = False
            if not ok:
                break
            n += 1

        p.set(self._name, slist)
        return n

    def _print(self, name, v, file):
        print(self._name, end = ' ', file = file)
        for c, s in v:
            print(f"{c:02d}:{s:02d}", end = ' ', file = file)
        print(file = file)

# Define the parameters that can appear in the parameter file to
# specify which sensors are references, primaries, or ADCs.

# @@@ fif2ctf could use this parameter file instead of the jig.def file.

sens_p = Param()

#sens_p.mkDesc('JigDef', 'j', Filename(), arghelp="JIGFILE", default="jig.def",
#    help="The name of a file to store the jig layout.")
sens_p.mkDesc('RefList', None, SList(), listValue=True, arghelp="SENSORLIST",
    help="A list of reference sensors.", default=[])
sens_p.mkDesc('PrimList', None, SList(), listValue=True, arghelp="SENSORLIST",
    help="The list of primary sensors.", default=[])
sens_p.mkDesc('ADCList', None, SList(), listValue=True, arghelp="SENSORLIST",
    help="A list of ADC channels.", default=[])




class SensorManager:

    def __init__(self):

        self.sensID = []

        self.refList = []
        self.primList = []

        self.refInChass = []
        self.primInChass = []
        self.refInArray = []
        self.primInArray = []

        self.dfcList = []
        self.dfcInChass = []

        self.selInChass = []
        self.selInArray = []
        self.selCSs = []

        self.ADCchass = []

    def info(self, message):

        return self.logger.info(message)

    def debug(self, message):

        return self.logger.debug(message)
    
    def error(self, message):
        
        return self.logger.error(message)

    def mapChassTupToInd(self, chanList):

        """ get sensID index in chassis"""

        indxInChass = [self.sensID.index(cs_pair) for cs_pair in chanList if cs_pair in self.sensID]
        
        self.debug(f"indxInChass: {indxInChass}")
        
        # [self.sensID.index((cs_pair[0],cs_pair[1])) for cs_pair in chanList if cs_pair in self.sensID]

        return indxInChass

    def mapChassToArr(self, tupListType):

        """ chassis indices to array indicesK """

        df = pd.read_pickle(os.path.join(current_path,"opmArray_7x8/sensorPosMap.pkl"))

        all_s = np.array(df.loc[:,"Sensor#InLab"])
        all_c = np.array(df.loc[:,"Chassis#InLab"])

        sensIDinArray = [(all_c[ii],all_s[ii]) for ii in range(len(all_s))] # make it the same format as sensID  


        chanTupList = self.tupListTypeToTupList(tupListType)

        chassInArray = [sensIDinArray.index(tup) for tup in chanTupList if ((tup in sensIDinArray) and (tup in self.sensID))]

        self.debug(f"len(sensIDinArray): {len(sensIDinArray)}")

        # check that selected tuples and indices in array agree

        _ = [sensIDinArray.index(tup) for tup in chanTupList if (tup in sensIDinArray) and (tup in self.sensID)]
        self.debug(f"selected indices: {_}\n")

        return np.array(chassInArray)


    def tupListTypeToTupList(self, tupListType):

        if tupListType in [1,'ref']:
            chanTupList = self.refList
        elif tupListType in [2, 'prim']:
            chanTupList = self.primList
        elif tupListType in [3, 'mag']:
            chanTupList = self.refList + self.primList
        elif tupListType in [4, 'dfc']:
            chanTupList = self.dfcList
        elif tupListType in [5, 'ref_dfc']:
            chanTupList = self.refList + self.dfcList
        else:
            chanTupList = []
        
        #print("CHANTUPLIST", chanTupList, "TUPLISTYPE", tupListType)
        
        return chanTupList

    def tupListToStrList(self, chanTupList, closedLoop):

        suffix = 50 if closedLoop else 28
        chanList = [ f"{c:02d}:{s:02d}:{suffix}" for c,s in chanTupList] 

        return chanList, str(suffix)


    def parseChanDict(self, ch_dict, tupListType, closedLoop):

        chanTupList = self.tupListTypeToTupList(tupListType)
        chanList, _ = self.tupListToStrList(chanTupList, closedLoop)

        calib, idx = [], []   

        for ch in ch_dict.keys():
            if ch in chanList:
                calib.append(ch_dict[ch]['calibration'])
                idx.append(ch_dict[ch]['idx'])
                
        return chanList, calib, idx   

    def getDFCSettings(self, ch_dict, dfcList_, closedLoop): 

        # define dfc-related indices depending on selected DFC option

        if self.runDFC > 1: # DFC prim + ref sensors 

            self.dfcList = cleanChanList(self.sensID, dfcList_)
            _, _, self.dfcInChass = self.parseChanDict(ch_dict, 'dfc', closedLoop)

            self.dfcInArray = self.mapChassToArr('dfc')
            self.selInChass = self.refInChass + self.dfcInChass  

            self.selInArray = np.array(self.mapChassToArr('ref_dfc'))
            _ = [self.sensID[ii] for ii in self.selInChass] # a@@ add list comprehension        
            self.selCSs = np.array(_) 

            self.debug(f"dfcInChass: {self.dfcInChass}")
            self.debug(f"dfcInArray: {self.dfcInArray}\n")
            self.info(f"selected DFC indices in chassis: {self.selInChass}")
            self.debug(f"selected DFC indices in array: {self.selInArray}\n")
            self.info(f"selected (c,s): {self.selCSs}\n")

        elif self.runDFC == 1: # DFC only in ref sensors @@@ this option is probably no longer needed

            self.dfcInChass = []
            self.selInChass = self.refInChass
            self.selInArray = self.refInArray
            self.selCSs = np.array(self.refList)

            self.info(f"selected DFC indices in chassis indx: {self.selInChass}")
            self.info(f"selected (c,s): {self.selCSs}\n")

        else: # no DFC

            self.dfcInChass = []
            self.selInChass = []
            self.selInArray = []
            self.selCSs = []
            self.dfcList = []

            self.info("NO DFC indices selected")

        return self

    def resetService(self, service):

        ch_dict = service.hardware_state.get_channel_dict()

        adcs = [int(ch.split(':')[0]) for ch in list(ch_dict.keys()) if ch in self.ADCnames]

        if len(adcs)>0:

            self.debug(f"found ADC channels {adcs} on. Settting them off...")

            for c in adcs:
                service.stop_adc(c)

            sensor_dict = {c: [(s,0,0,0) for s in ss] for c, ss in self.sdict.items()}
            service.adjust_fields(sensor_dict)

            self.debug(f"calling adjust fields with: {sensor_dict}")


    def extractFromStruct(self):

        return self.chassID, self.chNames_Ref, self.chNames_Prim, self.ADCnames, self.calib, self.selCSs, self.selInArray

    def prepareForDFC(self, service, s_data, p):

        # Get full list of sensor (c, s) pairs from the hardware.

        sensID = service.getSensors()

        # get sensor indices in chassis    

        self.refList = cleanChanList(sensID, p.RefList)
        self.primList = cleanChanList(sensID, p.PrimList)

        self.sensors = self.refList + self.primList
        self.sensID = cleanChanList(self.sensors, sensID) # use self.sensors instead of self.

        self.info(f"SensID: {self.sensID}\n")
        
        self.debug(f"Ref sensors: get indices in array from indices in chassis")
        self.refInArray = self.mapChassToArr('ref') 
        self.debug(f"Primary sensors: get indices in array from indices in chassis")
        self.primInArray = self.mapChassToArr('prim')

        self.chassID = slist2clist(self.sensID)
        self.sdict = slist2sdict(self.sensID)

        self.debug(f"sdict: {self.sdict}")

        # run restart | coarse | fine zeroing

        if p.restart:
            service.restartSensors(self.sdict, p.closedLoop)
        if p.coarseZero:
            service.coarseZero(self.sdict)
            s_data.CZ_coeffs = np.array(service.getCoeffs(self.sdict))
            print('after coarse zero', s_data.CZ_coeffs)
        if p.fineZero:
            service.fineZero(self.sdict)
            s_data.FZ_coeffs0 = service.getCoeffs(self.sdict)

        
        if len(service.get_not_ready()) == len(sensID): # all available sensors are OFF
        
            self.error("ALL SENSORS ARE OFF. quitting...")
            sys.exit(0)

        else:
        
            # ADC names
            self.adcList = p.ADCList
            self.ADCchas = slist2clist(p.ADCList)
            self.ADCnames = [ f"{c:02d}:00:0" for c in range(len(self.ADCchas))] 

            # if FL-API the program quit, reset service

            self.resetService(service)

            # get channel dictionary
            
            ch_dict = service.hardware_state.get_channel_dict()

            self.info(f"ch_dict: {ch_dict}\n")

            # parse name, calibration and indices based on channel type

            self.chNames_Ref, calib_Ref, self.refInChass = self.parseChanDict(ch_dict, 'ref', p.closedLoop)
            self.chNames_Prim, calib_Prim, self.primInChass = self.parseChanDict(ch_dict, 'prim', p.closedLoop)

            # log 

            self.debug(f"refList: {self.refList}")
            self.debug(f"refInChass: {self.refInChass}")
            self.debug(f"refInArray: {self.refInArray}\n")

            self.debug(f"primList: {self.primList}")
            self.debug(f"primInChass: {self.primInChass}")
            self.debug(f"primInArray: {self.primInArray}\n")


            # calibration for all meg sensors should be the same: 3.52 e-15 in CL, 1.0 in OL

            calib_sens = np.array(calib_Ref + calib_Prim)
            assert len(np.unique(calib_sens))==1, "calibration values are not unique amongst MEG sensors"
            self.calib = np.unique(calib_sens)[0]

            self.info(f"calib: {self.calib}")

            self.chNs = self.chNames_Ref + self.chNames_Prim


            # DFC settings

            self.runDFC = p.runDFC
            self = self.getDFCSettings(ch_dict, p.dfcList, p.closedLoop)

        return self, service


def slist2clist(slist):
    "Return a list of the chassis numbers found in a sensor list"

    l = []
    for c, s in slist:
        if c not in l:
            l.append(c)
    return l

def slist2sdict(slist):
    "Convert a sensor list [(c, s), ...] into a sensor dict {c: [s1, s2, ...], ...}"

    sdict = {}

    for c, s in slist:
        if not sdict.get(c):
            sdict[c] = []
        sdict[c].append(s)

    return sdict


def cleanChanList(template, chanList_):

    """ ensure that only channels that appear in template are used """

    chanList = [cs_pair for cs_pair in chanList_ if cs_pair in template]

    return chanList



def extractArrayInfo():

    # load sensor information  
    df = pd.read_pickle(os.path.join(current_path,'opmArray_7x8/sensorCoordAndAngles.pkl')) 

    # point 2 : base
    xpos_2 = np.array(df['Unnamed: 1'][3:],dtype='float')
    ypos_2 = np.array(df['Unnamed: 2'][3:],dtype='float')
    zpos_2 = np.array(df['Unnamed: 3'][3:],dtype='float')

    # point 3 : top
    xpos_3 = np.array(df['Unnamed: 4'][3:],dtype='float')
    ypos_3 = np.array(df['Unnamed: 5'][3:],dtype='float')
    zpos_3 = np.array(df['Unnamed: 6'][3:],dtype='float')

    # angles
    xAng_arr = np.abs(np.array(df['Unnamed: 7'][3:],dtype='float'))
    yAng_arr = np.abs(np.array(df['Unnamed: 9'][3:],dtype='float'))


    deltaX = (xpos_3-xpos_2)
    deltaY = (ypos_3-ypos_2)
    deltaZ = (zpos_3-zpos_2)

    NrRefs = 3
    NrPrims = len(xpos_2) 
    NrSens = NrPrims + NrRefs

    matrx = np.zeros([3,3,NrSens])
    cellCoords = np.zeros([NrSens,3])

    for m in range(NrPrims):

        bz = np.array([deltaX[m],deltaY[m],deltaZ[m]])
        bz /= np.linalg.norm(bz)

        # define auxiliary vectors in the JK, IK planes
        y1 = np.cos(np.deg2rad(90-yAng_arr[m])) # same direction as bx, which is aligned with J
        z1 = np.sin(np.deg2rad(90-yAng_arr[m]))*np.sign(ypos_2[m])
        x1 = 0
        v1 = np.array([x1,y1,z1]) # vector along the YZ plane (JK)

        x2 = -np.cos(np.deg2rad(90-xAng_arr[m])) # same direction as by, which is opposite direction to I
        z2 = np.sin(np.deg2rad(90-xAng_arr[m]))*np.sign(xpos_2[m])
        y2 = 0
        v2 = np.array([x2,y2,z2]) # vector along the XZ plane (IK)

        # bx, by, bz comprise a left-handed system
        bx = np.cross(v2,bz)
        bx /= np.linalg.norm(bx)

        by = np.cross(bz,v1)
        by /= np.linalg.norm(by)

        base_c = np.array([xpos_2[m],ypos_2[m],zpos_2[m]])

        cell_c = base_c + 5*bz #this is where the cell is located

        # store them in matrix
        matrx[0,:,m] = bx
        matrx[1,:,m] = by
        matrx[2,:,m] = bz

        cellCoords[m,:] = cell_c

    # ref sensors

    base_I = np.array([7.575, 0,0]) # provided by K.C.
    base_J = np.array([0, 7.575,0])
    base_K = np.array([0, 0, 6.5])

    bx_I, by_I, bz_I = np.array([0,1,0]), np.array([0,0,1]), np.array([1,0,0])
    bx_J, by_J, bz_J = np.array([1,0,0]), np.array([0,0,-1]), np.array([0,1,0])
    bx_K, by_K, bz_K = np.array([0,1,0]), np.array([-1,0,0]), np.array([0,0,1])

    cellCoords[m+1,:], cellCoords[m+2,:], cellCoords[m+3,:] = base_I + 5*bz_I, base_J + 5*bz_J, base_K + 5*bz_K

    matrx[0,:,m+1], matrx[1,:,m+1], matrx[2,:,m+1] = bx_I, by_I, bz_I
    matrx[0,:,m+2], matrx[1,:,m+2], matrx[2,:,m+2] = bx_J, by_J, bz_J
    matrx[0,:,m+3], matrx[1,:,m+3], matrx[2,:,m+3] = bx_K, by_K, bz_K

    return cellCoords, matrx



'''

def getIndArrays(sensID, refList, primList):
    """Return a list of the (c, s) pairs we are actually using, from sensID,
    along with the reference and primary indices into sensID."""

    slist = refList + primList
    for c, s in slist:
        if (c, s) not in sensID:
            raise RuntimeError(f"The specified sensor {c:02d}:{s:02d} is not available.")

    refInd = []
    for c, s in refList:
        refInd.append(sensID.index((c, s)))

    primInd = []
    for c, s in primList:
        primInd.append(sensID.index((c, s)))

    return slist, refInd, primInd

'''