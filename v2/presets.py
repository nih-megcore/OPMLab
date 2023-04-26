
import copy
import pandas as pd
import numpy as np
from constants import *
    

def createPreset(p, logger, printControl = False):
    
    df = pd.read_pickle("./opmArray_7x8/sensorPosMap.pkl")
    cs_all = df.loc[:,["Chassis#InLab","Sensor#InLab"]].to_numpy()
    
    dfcList = []
    indx = np.arange(len(p.PrimList))    
    indx_ = []
    
    if p.presets == 1: # dfc = all primary sensors
        
        logger.info('Preset 1: dfc = all primary sensors')
        dfcList = p.PrimList.copy()
        indx_ = indx

    elif p.presets == 2: # dfc applied in checkerboard fashion with sensor 1 = dfc ON
        
        logger.info('Preset 2: dfc = checkerboard with s1 on')
        
        sel = [np.arange(0+(r*cols),cols+(r*cols),2) if r%2==0 else np.arange(1+(r*cols),cols+(r*cols),2)  for r in range(rows)]
        '''
        sel = []
        for r in range(rows):
            if r % 2 ==0: # even
                sel.append(np.arange(0+(r*cols),cols+(r*cols),2))
            else:
                sel.append(np.arange(1+(r*cols),cols+(r*cols),2))
        '''
        sel = np.array(sel).flatten()
        indx_ = indx[sel]
        
        
        dfcList = [(cs_all[i,0],cs_all[i,1]) for i in indx_]
        '''        
        s = df.loc[indx_,"Sensor#InLab"]
        c = df.loc[indx_,"Chassis#InLab"]
        dfcList = []
        for i in range(len(s)):
            dfcList.extend([(c.iloc[i],s.iloc[i])])
        '''
            
    elif p.presets == 3: # dfc applied checkerboard fashion with sensor 8 = dfc ON
        
        logger.info('Preset 3: dfc = checkerboard with s2 on')
        
        sel = [np.arange(1+(r*cols),cols+(r*cols),2) if r%2==0 else np.arange(0+(r*cols),cols+(r*cols),2)  for r in range(rows)]
        
        '''
        sel = []
        for r in range(rows):
            if r % 2 ==0: # even
                sel.append(np.arange(1+(r*cols),cols+(r*cols),2))
            else:
                sel.append(np.arange(0+(r*cols),cols+(r*cols),2))
        '''
        
        sel = np.array(sel).flatten()
        indx_ = indx[sel]

        dfcList = [(cs_all[i,0],cs_all[i,1]) for i in indx_]
        '''
        sel = np.array(sel).flatten()
        indx_ = indx[sel]
        s = df.loc[indx_,"Sensor#InLab"]
        c = df.loc[indx_,"Chassis#InLab"]
        dfcList = []
        for i in range(len(s)):
            dfcList.extend([(c.iloc[i],s.iloc[i])])
        '''
    elif p.presets == 4: # dfc applied to first 4 columns (1-4)
        
        logger.info('Preset 4: dfc applied to first 4 columns (1-4)')
        indx_ = [ np.arange(0,4)+(cols*i) for i in range(rows)]
        '''
        for i in range(rows):
            indx_.append(np.arange(0,4)+(cols*i))
        '''
        indx_ = np.array(indx_).flatten()
        
        dfcList = [(cs_all[i,0],cs_all[i,1]) for i in indx_]
        
        '''
        s = df.loc[indx_,"Sensor#InLab"]
        c = df.loc[indx_,"Chassis#InLab"]
        dfcList = []
        for i in range(len(s)):
            dfcList.extend([(c.iloc[i],s.iloc[i])])
        '''
    elif p.presets == 5: # dfc applied to last 4 columns (5-8)
        
        logger.info('Preset 5: dfc applied to first 4 columns (5-8)')
        
        indx_ = [np.arange(4,cols)+(cols*i) for i in range(rows)]
        indx_ = np.array(indx_).flatten()

        dfcList = [(cs_all[i,0],cs_all[i,1]) for i in indx_]
        '''
        s = df.loc[indx_,"Sensor#InLab"]
        c = df.loc[indx_,"Chassis#InLab"]
        
        dfcList = []
        for i in range(len(s)):
            dfcList.extend([(c.iloc[i],s.iloc[i])])
        '''
    elif p.presets == 6: # dfc applied to first 28 sensors
        
        logger.info('Preset 6: dfc applied to first 28 sensors')
        indx_ = indx[np.arange(0,int(len(indx)/2))]

        dfcList = [(cs_all[i,0],cs_all[i,1]) for i in indx_]
        '''
        s = df.loc[indx_,"Sensor#InLab"]
        c = df.loc[indx_,"Chassis#InLab"]
        dfcList = []
        for i in range(len(s)):
            dfcList.extend([(c.iloc[i],s.iloc[i])])
        '''
    elif p.presets == 7: # dfc applied to last 28 sensors
        
        logger.info('Preset 7: dfc applied to last 28 sensors')
        indx_ = indx[np.arange(int(len(indx)/2),len(indx))]

        dfcList = [(cs_all[i,0],cs_all[i,1]) for i in indx_]
        
        '''
        s = df.loc[indx_,"Sensor#InLab"]
        c = df.loc[indx_,"Chassis#InLab"]
        dfcList = []
        for i in range(len(s)):
            dfcList.extend([(c.iloc[i],s.iloc[i])])
        '''
    
    printStr = printSetup(indx_)
    logger.info(printStr)
    
    if printControl:
        control = df.loc[indx_,:]
        print(control)
    return dfcList



def printSetup(indx):


    printStr = '\n\t(top view - sensor cables always going towards the left ear of the participant)\t\t\n'
    printStr += '\n\t\t\t\tRIGHT (Ear) \t\t\n\n' 
    
    indx += 1 # 1 base
    
    notIndx = np.setdiff1d(np.arange(1,(rows*cols)+1),indx)
    c_ = 0
    for i in range(1,(rows*cols)+1):
        if i in indx: # dfc ON
            printStr += '\t' + 'x'
        elif i in notIndx: 
            printStr += '\t' + str(i)

        if i % cols == 0: # end of line
            c_ +=1
            if c_ == 4:
                printStr += '\t (BACK)'
            printStr += '\n'

    printStr +='\t||||||||||||||||||||||||||||||||||||||||||||||||||||||||||\n'
    printStr +='\t|||||||||||||||||||||||||||||||||||||||||||||||||||||||||| <-sensor cables\n'
    
    printStr += '\n\t\t\t\tLEFT (Ear) \t\t\n'
    
    return printStr