import mne
import numpy as np

def npy2fif_raw(sPath, rawADC, rawRef, rawPrim, chNames, calib):
    print("[npy2fif]")
    g = 1e9
    n_channels = len(chNames)
    sfreq = 1000
    
    nRef = rawRef.shape[1]-1

    #if rawPrim:    
    #    nPrim = rawPrim.shape[1]
        #nSamp = rawPrim.shape[0]
        #print(f"{nSamp} samples")

    if np.ndim(rawADC)>1:
        nSamp = rawADC.shape[0] 
        ii = rawADC.shape[1]
    elif np.ndim(rawADC)==1:
        nSamp = len(rawADC)
        ii =1

    print(f"{nSamp} samples")
    print(ii)
    # ADC and raw data
    if ii==1:
        ch_names = ['Input1']
    else:
        ch_names = []
        for aa in range(ii):
            ch_names.append('Input' + str(aa+1))
#    ch_names = []
    for name in chNames:
        ch_names.append(name+'-BZ_CL')
    print(ch_names)
    
    ch_types = ['stim']*ii + ['mag']*n_channels 
    info = mne.create_info(ch_names, ch_types=ch_types, sfreq=sfreq)
    info['description'] = sPath
    print(info)

    for n in range(ii, n_channels+ii):
        info['chs'][n]['cal'] = calib[n-ii]
        print(info['chs'][n]['cal'])
        #info['chs'][n]['fzCoeff'] = []
        #info['chs'][n]['fzCoeff'] =  fzCoeffs[n-ii,:]
        
         
    for aa in range(ii):
        info['chs'][aa]['cal'] = 2.980232238769531e-07     
    
    #if rawRef and rawPrim:
    #    dat = np.concatenate((rawRef[:,1:]/g, rawPrim/g), axis = 1)
    #elif rawRef:

    if ii==1:
        rawADC.shape = (rawADC.shape[0],1)
    dat = np.concatenate((rawADC, rawRef[:,1:]/g), axis = 1)
   
#    dat = rawRef[:,1:]/g
    #else:
    #    dat = rawPrim/g    
    dat = dat.T
    

    """    
    temp = np.zeros((1 + nRef + nPrim + (nRef + nPrim)*2 + nPrim, nSamp))

    temp[0,:] = rawADC

    for i in range(nRef):
        temp[i+1,:] = rawRef[:,i+1] / g

    for i in range(nPrim):
        temp[i+1+nRef,:] = rawPrim[:,i] / g
        
    """

    raw = mne.io.RawArray(dat,info)
    raw.save(sPath+ '_raw.fif', overwrite=True)
