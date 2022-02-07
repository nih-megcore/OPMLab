import mne
import numpy as np

def npy2fif(sPath, rawADC, rawRef, rawPrim, chNames, calib):
    print("[npy2fif]")
    g = 1e9
    n_channels = len(chNames)
    sfreq = 1000

    ch_names = ['Input1']
    for name in chNames:
        ch_names.append(name+'-BZ_CL')
    print(ch_names)

    ch_types = ['stim'] + ['mag']*n_channels
    info = mne.create_info(ch_names, ch_types=ch_types, sfreq=sfreq)
    info['description'] = sPath
    print(info)

    # add calibration information

    for n in range(1, n_channels+1):
        info['chs'][n]['cal'] = calib[n-1]
        print(info['chs'][n]['cal'])

    info['chs'][0]['cal'] = 2.980232238769531e-07

    nRef = rawRef.shape[1]-1
    nPrim = rawPrim.shape[1]
    nSamp = len(rawADC)
    print(f"{nSamp} samples")
    temp = np.zeros((1 + nRef + nPrim, nSamp))

    temp[0,:] = rawADC

    for i in range(nRef):
        temp[i+1,:] = rawRef[:,i+1] / g

    for i in range(nPrim):
        temp[i+1+nRef,:] = rawPrim[:,i] / g

    raw = mne.io.RawArray(temp,info)
    raw.save(sPath + '_raw.fif', overwrite=True)
