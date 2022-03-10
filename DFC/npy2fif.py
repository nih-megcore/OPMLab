import mne
import numpy as np

def npy2fif(sPath, sensID, rawADC, rawRef, rawPrim, chNames, calib, compRef, compPrim, grad):
    print("[npy2fif]")
    g = 1e9
    n_channels = len(chNames)
    sfreq = 1000

    nRef = rawRef.shape[1]-1
    nPrim = rawPrim.shape[1]
    if np.ndim(rawADC)>1:
        nSamp = rawADC.shape[0] 
        ii = rawADC.shape[1]
    elif np.ndim(rawADC)==1:
        nSamp = len(rawADC)
        ii =1
    else:
        nSamp = rawRef.shape[0]
        ii = 0
    print(f"{nSamp} samples")
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
    ch_types = ['stim']*ii + ['mag']*n_channels + ['mag']*n_channels*2 + ['grad']*(n_channels-nRef)
    print(len(ch_types))
    info = mne.create_info(ch_names, ch_types=ch_types, sfreq=sfreq)
    info['description'] = sPath
    print(info)

    # add calibration information
    # ADC and raw data
    print(calib)

    for n in range(ii, n_channels+ii):
        info['chs'][n]['cal'] = calib[sensID[n-ii]]
        print(info['chs'][n]['cal'])      
         
    for aa in range(ii):
        info['chs'][aa]['cal'] = 2.980232238769531e-07
    
    print(n)
    # compensation fields bx,by 
    
    for n in range(n_channels*2):
        info['chs'][n+n_channels+ii]['cal'] = 1e-15
  
    print(n+n_channels+ii)
    # gradiometer response 
   
    for n in range(n_channels-3):
        print(len(info['chs']),n+(n_channels*3)+ii)
        info['chs'][n+(n_channels*3)+ii]['cal'] = 1e-15
 
    print(n+(n_channels*3)+ii)         
    global dat
    print(rawADC.shape, rawRef.shape, rawPrim.shape)
    if ii==1:
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
