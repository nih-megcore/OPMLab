import mne
import numpy as np

def npy2fif(sPath):
    data = {}

    coeffs = np.load(name + '_coeffs.npy') # fine-zero coefficients

    rawADC = np.load(name + '_rawADC.npy') # adc channel    
    rawRef = np.load(name+ '_rawRef.npy') # raw reference sensor timecourses
    rawPrim = np.load(name + '_rawPrim.npy') # raw primary sensor timecourses

    filtData = np.load(name + '_filt.npy') # ema filtered reference sensor timecourses

    compRef = np.load(name + '_compRef.npy') # compensation fields (bx,by) for the references
    compPrim = np.load(name + '_compPrim.npy') # compensation fields (bx,by,bz) for primary sensors

    gradData = np.load(name +'_gradPrim.npy') # 1st order gradiometer for primary sensors

    refInd = np.load(name +'_refInd.npy') # 1st order gradiometer for primary sensors
    primInd = np.load(name +'_primInd.npy') # 1st order gradiometer for primary sensors
    dfcInd = np.load(name +'_dfcInd.npy') # 1st order gradiometer for primary sensors
    chNames = np.load(name +'_chanNames.npy') # 1st order gradiometer for primary sensors    
    calib = np.load(name+'_calib.npy')


    data['ADC'] = rawADC
    data['rawRef'] = rawRef
    data['rawPrim'] = rawPrim

    data['filtRef'] = filtData

    data['coeffs'] = coeffs

    data['compRef'] = compRef
    data['compPrim'] = compPrim

    data['gradPrim'] = gradData

    data['refInd'] = refInd
    data['primInd'] = primInd 
    data['dfcInd'] = dfcInd
    data['chNames'] = chNames
    data['calib'] = calib

    indxRef = data['refInd']
    faultySens = [14]
    indxPrim = data['primInd']
    g = 1e9
    if faultySens:
        # shift back indices larger than faulty sens
        tmp = np.where(indxPrim>faultySens[0])[0]
        indxPrim[tmp]=indxPrim[tmp]-1

    n_channels = len(data['chNames'])
    sfreq = 1000

    ch_names = []

    for i in data['chNames']:
        ch_names.append(i+'-BZ_CL')

    print(ch_names)

    ch_types = ['stim'] + ['mag']*n_channels
    info = mne.create_info(['Input1']+ch_names,ch_types = ch_types, sfreq = sfreq)
    info['description'] = filename
    print(info)

    # add calibration information

    for n in range(1,n_channels+1):
        info['chs'][n]['cal'] = calib[n-1]
        print(info['chs'][n]['cal'])

    info['chs'][0]['cal'] = 2.980232238769531e-07

    temp = np.zeros([len(data['refInd']) + len(data['primInd']) + 1, len(data['ADC'])])
    for s in range(len(refInd)):
        print(refInd[s])
        temp[refInd[s],:] = data['rawRef'][:,s+1].T / g

    for s in range(len(indxPrim)):
        print(indxPrim[s])
        temp[primInd[s],:] = data['rawPrim'][:,s].T / g

    temp[0,:] = data['ADC'].T

    raw = mne.io.RawArray(temp,info)
    raw.save(filename + '_raw.fif', overwrite=True)
