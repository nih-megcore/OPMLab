import mne
import numpy as np

def npy2fif_raw(sPath, rawRef, rawPrim, chNames, calib):
    print("[npy2fif]")
    g = 1e9
    n_channels = len(chNames)
    sfreq = 1000

    nRef = rawRef.shape[1]-1
    nPrim = rawPrim.shape[1]
    nSamp = rawPrim.shape[0]
    print(f"{nSamp} samples")

    ch_names = []
    for name in chNames:
        ch_names.append(name+'-BZ_CL')
    print(ch_names)
    
    ch_types = ['mag']*n_channels 
    info = mne.create_info(ch_names, ch_types=ch_types, sfreq=sfreq)
    info['description'] = sPath
    print(info)

    for n in range(n_channels):
        info['chs'][n]['cal'] = calib[n-1]
        print(info['chs'][n]['cal'])       
    
    dat = np.concatenate((rawRef[:,1:]/g, rawPrim/g), axis = 1)

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
