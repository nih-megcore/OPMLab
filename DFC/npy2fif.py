import mne
import numpy as np

def npy2fif(sPath, rawADC, rawRef, rawPrim, chNames, calib, compRef, compPrim, grad):
    print("[npy2fif]")
    g = 1e9
    n_channels = len(chNames)
    sfreq = 1000

    nRef = rawRef.shape[1]-1
    nPrim = rawPrim.shape[1]
    nSamp = len(rawADC)
    print(f"{nSamp} samples")


    # ADC and raw data
    ch_names = ['Input1']
    for name in chNames:
        ch_names.append(name+'-BZ_CL')
    print(ch_names)
    
    # append compensation fields in bx, by as 'mag' types
    coils = ['bx','by']
    for name in chNames:
        for c in coils:
            ch_names.append(name + '_' + c)
    print(ch_names)
    
    # append 1st order gradiometer response for primary sensors as 'grad' types
    for name in chNames[nRef:]: # exclude references
        ch_names.append(name + '_grad')
    print(ch_names)

    global info
    ch_types = ['stim'] + ['mag']*n_channels + ['mag']*n_channels*2 + ['grad']*(n_channels-nRef)
    print(len(ch_types))
    info = mne.create_info(ch_names, ch_types=ch_types, sfreq=sfreq)
    info['description'] = sPath
    print(info)

    # add calibration information
    # ADC and raw data
    for n in range(1, n_channels+1):
        info['chs'][n]['cal'] = calib[n-1]
        print(info['chs'][n]['cal'])

    info['chs'][0]['cal'] = 2.980232238769531e-07
    print(n)
    # compensation fields bx,by 
    
    for n in range(n_channels*2):
        info['chs'][n+n_channels+1]['cal'] = 1e-15
    print(n+n_channels+1)
    # gradiometer response 
   
    for n in range(n_channels-3):
        print(len(info['chs']),n+(n_channels*3)+1)
        info['chs'][n+(n_channels*3)+1]['cal'] = 1e-15
    print(n+(n_channels*3)+1)         
    global dat
    print(rawADC.shape, rawRef.shape, rawPrim.shape)
    rawADC.shape = (rawADC.shape[0],1)
    dat = np.concatenate((rawADC, rawRef[:,1:]/g, rawPrim/g), axis = 1)
    
    crefs = compRef.reshape(compRef.shape[0],compRef.shape[1]*2)
    cprims = compPrim[:,:,0:2]
    cprims = cprims.reshape(compPrim.shape[0],compPrim.shape[1]*2)
    
    dat = np.concatenate((dat,crefs/g,cprims/g,grad/g), axis =1)
    dat = dat.T
    print(dat.shape)

    raw = mne.io.RawArray(dat,info)
    raw.save(sPath + '_raw.fif', overwrite=True)
