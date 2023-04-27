# Dynamic Field Compensation

The software in this repository has been developed at the NIMH MEG Core Facility. This code requires FieldLine's (FL) API to dynamically correct the fields measured by their OPMs. 

The version of the programs used in [Robinson et al., 2022](https://www.sciencedirect.com/science/article/pii/S1053811922006747?via%3Dihub) can be found in the **/v1** directory. This release was developed using FL v2 sensors, and tested on a setup with n=19 sensors (16 primary sensors arranged in a 4x4 grid, and 3 orthogonally arrranged reference sensors above the array).

Programs in **/v2** correspond to the Spring 2023 release. This release was developed using FL v2 sensors, FL-API 0.4.3, and tested on a setup with n=59 sensors (56 primary sensors arranged in a 7x8 grid, and 3 orthogonally arrranged reference sensors above the array).

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

(to do)

#### output

(to do)

**Requirements**:

(to do > add cross platform yml file)
- Fieldline API >=0.4.2 [?]
- Setup-specific sensor coordinates & coordinate systems - see wiki page [wip]
- Currently only working with Python 3.9
