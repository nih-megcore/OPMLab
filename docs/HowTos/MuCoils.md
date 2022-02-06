# ... set up the (Active) Shielding system

The Mu Coil system is an active shielding system* that allows us to remove the remnant magnetic field that is present inside the MSR. This section focuses on how to to set up the system. For more information on how to set up the system, please take a look at the Mu Coil system manual located behind the linux computer
:::{note}
We are currently using the Mu Coils as a static shielding system
:::

### Placement of the Mu coils

This arrangement leaves enough room for the fluxgates, but it may need to be modified depending on the setup. See the schematic figure below.

```{figure} ../attachments/muCoilSetup.png
:height: 450px
:name: mucoils
	
Schematic representation of setup.
```

:::{note}
Place the panel spacer to ensure the correct distance between the 2 coils. One of the handles of the panel spacer may not be fully in! it needs glued in!
:::


### Active Field nulling process (wip)
1. Switch on electronics units (under the desk)
2. On the acquisition laptop (login pin on the screen),set the fluxgate offsets to 0: in the fluxgate_offsets.txt file type 6 zeros, tab spaced. This file can be found in xxxx
3. Open MSL coil control software (magnetometer offsets should now be 0)
:::{important}
The coil cabinet contains the three coil drivers each with three dials on the front. There are switches beneath the three dials which glow red if they are on. For these recordings they should all either be switched off or have the dials set to 5 (5=0V applied to the coils). If this was not the case then the field zero values will need to be re-measured as they will reflect the background field plus the coil field rather than the pure background field (you will not need to do the drift recordings again).
:::
4. Place Fluxgate sensors in position 1. When stable, write the integers down in the python script fluxgate.py (located at "/home/holroydt/mucoil") on the linux computer (log in as Tom). Do the same thing for positions 2 and 3
5. Close MSL coil control
6. Run the fluxgate.py script. It will output the field offset values:
```
-225.0  -184.0  -207.5  -116.0  -262.0  -182.0
```
7. Add them to the fluxgate_offsets.txt file. Reopen MSL coil control software. You should see the previous output there
6. Adjust voltage drivers (in the electronics unit) for Bz,By,Bx (in that order) **slowly**. When fields <-1nT, stop
7. Click on Lock Voltages to close the MuCoil gui



### Setting up the QuSpin sensors


(TO DO -- DIAGRAM OF CONNECTIONS)
- Each sensor has a usb that has to be connected to the laptop (other usb connections may need to be disconnected)!
- Switch on the power for each sensor
- Open quSpin ZFM (I used version V7.5.1), from the user's manual:

```
Step 1: Press the [Auto Start] button (3) to bring the sensors online. The startup process takes a few minutes to complete, as indicated by the first three LEDs turning green. The ‘Laser On/Off LED’ will turn green to indicate that the laser is on. Next, the ‘Laser Lock’ LED will turn green when the laser frequency is locked. Finally, the ‘Cell T Lock’ LED will turn green when the vapor cell is at optimal temperature.

Step 2: Once the first three LEDs are green, press the [Field Zero] button (4) once to activate field zeroing. The button will turn amber color while active. When the field values for B0, By, and Bz stop fluctuating (to within a few 100 pT, usually taking between 5-10 seconds), press the [Field Zero] button a second time to stop the process and lock the compensation fields. The fourth LED turns green indicating the compensations fields are applied.

Note: It is necessary to repeat the [Field Zero] operation every time the ‘Sensitive Axis’ is switched to a different mode or the background field is expected to have changed significantly (e.g. opening and closing the shields, or moving the sensors).

Step 3: When all 4 LEDs are green, press the [Calibrate] button (5). Wait for calibration values to appear sequentially in each corresponding ‘Sensor Status’ box (this process takes a few seconds per sensor). Calibration values less than 1.5 are considered normal and indicate optimal performance. Calibration values above 1.5 indicate sub-optimal sensor performance, either due to large background field (> 50 nT), or a possible sensor issue.
```


### Measuring with DAQExpress

- Disconnect one of the usb cables so that the NI-9205 device can be connected to the laptop (OPMs are wired to this device)
- Once the usb connected, a window will pop up. Select Go on the right side of DAQExpress.
- Now you can create a new project or load one created previously
- If new project: create analog input project (this option measures sensor and electrical signals)
  - The ai20-23 are the differential inputs (this should be automatically detected by the software)
  - The ai29-31 are the references (also automatically detected)

Understanding which components of which OPM sensor corresponds to each channel 

|           |  BZ (pin) | BZ (ai)  | BY (pin)   | BY (ai)  |
|-----------|-----------|----------|------------|----------|
| T (OPM 2) | 17(+)     | 22       | 18(+)      | 23       |
|           | 36(-)     | 30       | 37(-)      | 31       |
| U (OPM 1) | 15(+)     | 20       | 16(+)      | 21       |
|           | 34(-)     | 28       | 35(-)      | 29       |

