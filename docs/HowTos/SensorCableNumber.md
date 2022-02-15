# ... place sensors in 4x4 fixture

Each chassis contains 16 sensors, numbered 1-16. We thus have 4x sensor1, 4x sensor 2, etc. In the FieldLine GUI, they are distinguishable because the chassis number is used when all of them are connected, i.e., 
```
00:01
01:01
02:01
03:01
```
correspond to sensor 1 in chassis 0-3. 


Each of the 64 sensors has a unique serial number and cable number. The serial number is accessible through the API or the FielLine recorder. The cable number is pasted on the cable that connects the opm to the chassis. This is the table with the correspondence between sensor and chassis # and the cable #

```{figure} ../attachments/chassSensCableNumbers.png
:height: 450px
:name: chassSensCableNumbers
	
This figure/table shows the correspondence between chassis, sensor and cable numbers.
```

The convention we are using to place the sensors of a given chassis is described in this [figure](calib_20210813-14_2)