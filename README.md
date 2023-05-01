# Dynamic Field Compensation

This implementation of dynamic field compensation (DFC) aims to mitigate cross-axis projection errors (CAPE) by maintaining each OPM sensor close to zero-field along its transverse axes (x,y); it does that by applying transformed field measurements from 3 designated magnetometers (here on defined as reference magnetometers) to the on-sensor coils along the transverse axis. The implementationsthat have been released so far assume that Fieldline (FL) V2 sensors are used and that the sensors are operated in closed loop mode.

The software in this repository has been developed at the NIMH MEG Core Facility. This code requires FL API to dynamically correct the fields measured by their OPMs. 

The version of the programs used in [Robinson et al., 2022](https://www.sciencedirect.com/science/article/pii/S1053811922006747?via%3Dihub) can be found in the **/v1** directory. This release was developed using FL V2 sensors, and tested on a setup with n=19 sensors (16 primary sensors arranged in a 4x4 grid, and 3 orthogonally arrranged reference sensors above the array).

Programs in **/v2** correspond to the Spring 2023 release. This release was developed using FL V2 sensors, FL-API 0.4.3, and tested on a setup with n=59 sensors (56 primary sensors arranged in a 7x8 grid, and 3 orthogonally arrranged reference sensors above the array).

### RELEASE NOTES
#### V2
**New features/enhancements**
- to avoid the blocking behavior of *queue* .put() and .get(), *queue* was replaced with a *deque*, for which .append() and .popleft() have no locks, and a threading.Event() was used to synchronize access to the *deque*.
- *get_data* may place >=1 items in the *deque* when it is called. To ensure all samples are recorded properly, a loop is called to empty *deque* before allowing new items to populate *deque*
- compensation fields are computed only for the last item in the *deque*. In turn, *adjust_fields()* - the function that modifies the internal coil currents based on the compensation fields - is not necessarily called at every sample. To illustrate this, suppose the first adjust_fields() was called at t=0 samples, and the next adjust_fields() was called at t=4 samples. During the interval where *adjust_fields()* is not called (t=[1,2,3]samples), internal coil currents are based on the compensation fields computed at t=0 samples.
- compensation fields are computed for all sensors at once using tensor multiplication
- recording duration is now set based on elapsed samples instead of elapsed time

### USAGE 

#### general
- *example_param.param* is used to provide input parameters -- see below
- the flags *-r,-c,-f* do sensor restart, coarse zero, and fine zero, respectively; they are not required if sensors have already been restarted/coarse zeroed/fine zeroed
- right before data start being recorded, a fine zero is carried out to minimize field offsets (even if -f was not set)
- example commands
``` 
DFC_7x8.py --param example_param.param -r -c -f # do restart, coarse zero, fine zero at the beginning
DFC_7x8.py --param example_param.param -c -f # only do coarse zero and fine zero
DFC_7x8.py --param example_param.param # don't do any
```

#### .param file

It is a convenient approach to define a set of input parameters from a single file.
- _ipList_: the ip address(es) of the chassis that the user wants to operate. It should follow the same order as the daisy-chained chassis in the lab, starting with the Master chassis. 
- _savePath_ & _savename_: saving directory / filename
- _runDFC_: 0 [no DFC] or 2 [apply DFC to all sensors] 
- _Dur_: experiment duration, in seconds
- _coilID_: this parameter is specific to the NIH setup and it controls which coil will be energized during calibration. A calibration electronics box is connected to the acquisition computer and to a calibration prism that contains 20 coils. _coilID_ is used as an input to the _numato_ class (defined in numato.py), which sends coil activation/stop command to a USB port in the calibration box. Set it to -1 if to disable this option
- _ADCList_: list of ADC channels to record from
- _Ref_: list of magnetometers that operate as reference sensors
- _Prim_: list of magnetometers that operate as primary sensors
- _presets_: if runDFC is set to 2, _presets_ provides a shortcut to select a pre-defined sensor pattern to which DFC will be applied. These presets were defined based on the 7x8 sensor grid.  preset = 1 applies DFC to all primary sensors; presets 2,3 apply DFC to primary sensors in a checkerboard fashion (with half of the sensors having DFC ON); presets 4,5,6,7 apply DFC to half of the sensors in the setup, either column-wise or row-wise. 

![alt text](https://user-images.githubusercontent.com/74140759/235463624-dcb93fef-cf2c-4365-be71-6a678fe584a4.png)

- _Filter_: the following options have been implemented so far: 
  - exponential moving average, with the time constant _tau_ used to define the cutoff at -3dB
    ```
    import numpy as np
    
    Fs = 1000 # sampling rate 
    tau = 0.005 # in seconds
    a = np.exp(-1 / (tau * Fs))
    cutoff = Fs * (1 - a) / (2 * np.pi * a)
    ```
  - chebyshev type 2 
  - elliptical 

An example .param file can be found under /v2/exampleParam.param. In this example, we used 4 chassis.
```
ipList 192.168.1.43,192.168.1.44,192.168.1.40,192.168.1.42	# no space allowed

savePath data/{datestamp}
saveName test 

runDFC 0 # 0 = noDFC; 2 = DFC applied to ALL sensors
Dur 30 # in seconds
coilID -1 # for calibration

ADCList 00:00 01:00 02:00 03:00
Ref 00:09 00:10 00:11 
Prim 00:01 00:02 00:03 00:04 00:05 00:06 00:07 00:08 01:* 02:* 03:*
presets 1 # shortcut to control onto which sensor DFC is applied [1-7, check presets.py] 

Filter cheby2 cutoff=13 #ema tau=0.03

Closedloop True
```


#### output

(to do)

**Requirements**:

(to do > add cross platform yml file)
- Fieldline API >=0.4.2 [?]
- Setup-specific sensor coordinates & coordinate systems - see wiki page [wip]
- Currently only working with Python 3.9
