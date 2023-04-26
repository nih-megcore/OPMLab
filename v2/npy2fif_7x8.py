
import numpy as np
import mne 
from constants import *
from mne.transforms import apply_trans
import tensorly as tl
from filters import *


def computeSynthGrad(s_data,s_sens, s_geom):

    ''' compute synthetic gradiometer offline'''

    compM = tl.tenalg.mode_dot(s_geom.rotMat[:,:,s_sens.primInArray],s_data.rawDataRef,mode=1) # nRefs x nTimes x nPrim. nRefs = bx,by,bz
    gradPrim = s_data.rawDataPrim - compM[2,:,:] # data - bz | nTImes x nPrim

    return gradPrim

def filterRefSens(s_data, filter_ref):

    ''' filter ref sensors offline'''

    filter_ref.restart()
        
    filtDataRef = np.empty(s_data.rawDataRef.shape)
    for n in range(s_data.rawDataRef.shape[0]):    
        filtDataRef[n,:] = filter_ref(s_data.rawDataRef[n,:])

    return filtDataRef

def renameMEGChanAndGetInd(s_sens):

    ''' 
    data will be stored in increasing cc:ss manner
    - get channel indices that follow this sorting order
    - get channel names from API [{cc}:{ss}:{opMode}] and put them in FL output format [FL{cc}{ss}-BZ_{opMode}] 
   
    '''

    indx = struct()

    # initialize variables
      
    opMode =  'CL' if s_sens.chNs[0].split(':')[-1]=='50' else 'OL'
    ch_names, ch_names_fRefs, ch_names_grad = [] , [], []       
    i_ref, i_prim = [], []
    ii, c_ref, c_prim = -1, -1, -1
    
    # rename channels so that output channels are in the same format as FL recorder
    # store calibration values, channel names, indices according to the order in FL recorder (sensID follows this order)
    
    for c, s in s_sens.sensID:

        s_ = f"0{s}" if s < 10 else str(s)
        chName = 'FL0'+ str(c+1) + str(s_) # chassis are 1-based
        
        if (c,s) in s_sens.refList:

            # append channel name to lists
            ch_names.append(chName + '-BZ_' +  opMode)
            if s_sens.runDFC>0:
                ch_names_fRefs.append(chName + '_filt-BZ_' + opMode)

            # append values to ind lists
            c_ref +=1
            ii +=1
            i_ref.append(ii)
            

        elif (c,s) in s_sens.primList:

            # append channel name to lists
            ch_names.append(chName + '-BZ_' +  opMode)
            if s_sens.runDFC>1:
                ch_names_grad.append(chName +'_grad-BZ_' + opMode)
            
            # append values to ind lists
            c_prim +=1
            ii +=1
            i_prim.append(ii)

    
    indx.i_ref = np.array(i_ref)
    indx.i_prim = np.array(i_prim)

    assert (len(i_ref)+len(i_prim))==len(ch_names)

    s_sens.debug(f"i_prim {indx.i_prim}")
    s_sens.debug(f"i_ref {indx.i_ref}")

    # first append gradiometer names, then filtered ref sensor names

    if s_sens.runDFC > 1:
        ch_names += ch_names_grad 
        indx.i_grad = np.arange(ii+1, len(ch_names))
        s_sens.debug(f"grads {indx.i_grad}")
    
    if s_sens.runDFC > 0:
        ch_names += ch_names_fRefs
        indx.i_fRefs = np.arange(indx.i_grad[-1]+1, len(ch_names))
        s_sens.debug(f"filt refs {indx.i_fRefs}")

           
    return ch_names, indx


def npy2fif(s_data, s_sens, s_geom, filter_ref, sPath):
    
    '''convert numpy arrays to fif format'''

    # filter refs and do synthetic gradiometry
    
    if s_sens.runDFC > 0 :
        filtDataRef = filterRefSens(s_data, filter_ref)
        s_sens.debug(" filtering ref sensors") 

        if s_sens.runDFC>1: 
            s_sens.debug("computing software gradiometers") 
            gradPrim = computeSynthGrad(s_data,s_sens, s_geom)
        
    ch_names, indx = renameMEGChanAndGetInd(s_sens)
    
    # define ch_types without adc channels

    ch_types = ['mag']*len(ch_names)

    # adc channels
    ch_names_adc = [f"Input{adc+1}" for adc in range(len(s_sens.ADCchas))]
    ch_names += ch_names_adc
    indx.i_adc = np.arange(len(ch_types),len(ch_names))

    # append adc channels

    ch_types += ['stim']*len(ch_names_adc) 

    assert(len(ch_types)==len(ch_names))

    # create info file

    info = mne.create_info(ch_names, ch_types = ch_types, sfreq = fs)
    info['description'] = sPath

    # preallocate memory for raw data

    data = np.empty([s_data.rawDataPrim.shape[0],len(ch_names)]) 

    # populate info and data in loop

    trans = np.array([[0,-1,0,0],[1,0,0,0],[0,0,1,0],[0,0,0,-90]]) 
    c_ref, c_prim, c_adc = -1, -1, -1 # counter for ref | prim | adc 

    for i_ch in range(len(ch_names)):

        # ADC channels

        if i_ch in indx.i_adc:
            info['chs'][i_ch]['cal'] = calib_ADC #2.980232238769531e-07
            c_adc +=1
            if len(s_sens.ADCchas)==1:
                data[:,i_ch] = s_data.rawDataADC
            else:
                data[:,i_ch] = s_data.rawDataADC[:,c_adc]

        # Ref, Prim [Grad, FiltRef]

        elif i_ch in np.concatenate((indx.i_ref,indx.i_prim)): 

            if i_ch in indx.i_ref:
                c_ref +=1
                ii = s_sens.refInArray[c_ref]
                s_sens.info(f"index in array {ii} ; ch_name: {ch_names[i_ch]}") 
                
                data[:,i_ch] = s_data.rawDataRef[:,c_ref]/g 
                
                if s_sens.runDFC>0:
                    i_syn = indx.i_fRefs[c_ref]
                    data[:,i_syn] = filtDataRef[:,c_ref]/g 
                
            else:
                c_prim +=1
                ii = s_sens.primInArray[c_prim]
                s_sens.info(f"index in array {ii} ; ch_name: {ch_names[i_ch]}") 

                data[:,i_ch] = s_data.rawDataPrim[:,c_prim]/g
                
                if s_sens.runDFC>1:
                    i_syn = indx.i_grad[c_prim]               
                    data[:,i_syn] = gradPrim[:,c_prim]/g
    
            # add sensor pos & orientation information for primary and ref sensors           

            info['chs'][i_ch]['cal'] = s_sens.calib # assuming all channels have same calibration
            info['chs'][i_ch]['loc'][:3] = apply_trans(trans,s_geom.cell_coords[ii,:])/1e3# in m 
            info['chs'][i_ch]['coord_frame'] = FIFF.FIFFV_COORD_DEVICE
            info['chs'][i_ch]['coil_type'] = FIFF.FIFFV_COIL_FIELDLINE_OPM_MAG_GEN1#FIFFV_COIL_VV_MAG_T3 

            # add sensor pos & orientation information for filt ref and synthetic gradiometers
            
            if s_sens.runDFC>0:
                info['chs'][i_syn]['cal'] = s_sens.calib # assuming all channels have same calibration
                info['chs'][i_syn]['loc'][:3] = apply_trans(trans,s_geom.cell_coords[ii,:])/1e3 # in m 
                info['chs'][i_syn]['coord_frame'] = FIFF.FIFFV_COORD_DEVICE
                info['chs'][i_syn]['coil_type'] = FIFF.FIFFV_COIL_FIELDLINE_OPM_MAG_GEN1 

    # adding coregistered sensor position to the MRI is done offline
    # set device to head transformation to None until then

    info['dev_head_t'] = None

    # create raw object

    data = data.T
    s_sens.info(f"data array shape {data.shape}") 

    s_sens.logger.info('saving raw mne object...') 
    raw = mne.io.RawArray(data,info)
    raw.save(sPath + '_raw.fif', overwrite=True)

    s_sens.info('done.') 