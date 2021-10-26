# Phase delays


### CTF data

We see a phase delay for the reference magnetometers, but we don't know why. 
For both CTF datasets, gradiometers are in phase. Reference magnetometers, while not perfect, look better for 13/10/21 than the 6/2/21 dataset.  Since we turned the amplitude of the calibrator up, there may be less influence of noise on the phase.

````{panels}
**CTF data: 2021/06/02 [4Vpp]**


```{figure} ../Open_Issues/attachments/20210602_PhaseOffset.png
:height: 250px
:name: 20210602_PhaseOffset
	
Phase delay for reference magnetometers. 
```                                             
---


**CTF data: 2021/10/13 [6Vpp]**

```{figure} ../Open_Issues/attachments/20211013_PhaseOffset.png
:height: 250px
:name: 20211013_PhaseOffset
	
Phase delay for reference magnetometers. 
```
````

### OPM data

#### Cross-talk
Allison took the timeseries data from all the sensors (including 6) and filtered it for a 20-34 Hz bandpass using an MNE-python zero-phase filter
For one sensor with an active Bz coil, there are the four nearest neighbor sensors, and then four more sensors that are diagonal from that sensor. When looking at those 8 sensors, they are very nearly in phase. 
The phase delay between the active coil and the nearest neighbors is either 82.2 or 83.2 degrees, depending on the sensor. 


````{panels}
**Phase delay observed during crosstalk**


```{figure} ../Open_Issues/attachments/20210821_XtalkPhaseShift.png
:height: 250px
:name: 20210821_XtalkPhaseShift 

Here, the Bz coil for sensor 6 was active. Note that the magnitude of the signal on the nearest neighbors is around 1e-3 times the magnitude on the active sensor, but the magnitude of the active sensor was scaled down for the visualization. 
```                                             
---


**Sensor arrangement**

```{figure} ../Open_Issues/attachments/20210821_SensArr.png
:height: 250px
:name: 20210821_SensArr

Sensor arrangement during calibration runs
```

````

```{admonition} Summary
:class: tip
- The CTF data seems to indicate that phase offsets in the reference magnetometers are dependent on the amplitude of the signal. A larger signal from the calibrator makes the phase offsets in the reference magnetometers significantly smaller -  indicating that the observed phase shifts at low amplitudes are a consequence of noise, not a product of a faulty calibrator.
- The OPM crosstalk data shows no phase shift amongst the nearest neighbor sensors, only a phase shift in the more remote sensors, which is likely due to noise. This would seem to indicate that the calibrator is the source of phase offsets, not the OPMs.
``` 


#### Calibration

Stephen looked at the OPM data from 2021/08/14 (closed loop). The phase errors seem to be associated with low crosspower

````{panels}
**2021/08/14: Phase vs Crosspower**

```{figure} ../Open_Issues/attachments/20210814_PhaseVsCrosspower.png
:height: 250px
:name: 20210814_PhaseVsCrosspower 

include caption
```                                             
---


**2021/08/14: sdev of Phase vs Crosspower**

```{figure} ../Open_Issues/attachments/20210814_StdDevPhaseVsCrosspower.png
:height: 250px
:name: 20210814_StdDevPhaseVsCrosspower

include caption
```
````



