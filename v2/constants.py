from mne.io.constants import FIFF

class struct:
    pass


### geometry-related ###

nChass = 4 # total chassis in setup
nSensPC = 16  # sensors per chassis (PC)

# array
rows = 7
cols = 8 

### -----------------###

# for DFC code

g = 1e9 # convert tesla to nanotesla
calib_ADC = 2.980232238769531e-07 # calibration value of adc channel
fs = 1000 # sampling rate

