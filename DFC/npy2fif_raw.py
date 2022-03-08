import mne
import numpy as np

def npy2fif_raw(sPath, rawADC, rawRef, rawPrim, chNames, calib):

    print("[npy2fif]")
    g = 1e9
    n_channels = len(chNames)
    sfreq = 1000

    if np.ndim(rawADC)>1:
        nSamp = rawADC.shape[0] 
        ii = rawADC.shape[1]
        print(f"{nSamp} samples")
    elif np.ndim(rawADC)==1 and len(rawADC)>0:
        nSamp = len(rawADC)
        ii =1
        print(f"{nSamp} samples")
    elif np.ndim(rawADC)==1 and len(rawADC)==0:
        ii = 0

    print(ii)
    # ADC and raw data
    if ii==1:
        ch_names = ['Input1']
    else:
        ch_names = []
        for aa in range(ii):
            ch_names.append('Input' + str(aa+1))
    for name in chNames:
        ch_names.append(name+'-BZ_CL')
    print(ch_names)
    
    global info
    ch_types = ['stim']*ii + ['mag']*n_channels
    print(len(ch_types))
    info = mne.create_info(ch_names, ch_types=ch_types, sfreq=sfreq)
    info['description'] = sPath
    print(info)

    # add calibration information
    # ADC and raw data
    print(calib)

    for n in range(ii, n_channels+ii):
        info['chs'][n]['cal'] = calib[n-ii]
        print(info['chs'][n]['cal'])       
         
    for aa in range(ii):
        info['chs'][aa]['cal'] = 2.980232238769531e-07
    print(n)
    
    global dat
    print(rawADC.shape, rawRef.shape, rawPrim.shape)
    if ii==1:
        rawADC.shape = (rawADC.shape[0],1)
    dat = np.concatenate((rawADC, rawRef[:,1:]/g, rawPrim/g), axis = 1)
    dat = dat.T
    print(dat.shape)

    raw = mne.io.RawArray(dat,info)
    raw.save(sPath + '_raw.fif', overwrite=True)