# To Dos

(This file has not been updated since ~July 2021)

- **Engineering Challenges:**
 
    - Strain relief and weight management for cabling to reduce participant neckstrain and strain on cable attachments to sensors.
        - Straps from ceiling
        - Support arm
    - Patient stabilization
        - Backboard/seatbelt and neck brace
        - Seated vs supine measurement -- supine will minimize need for restraints
    - Heat Mitigation
        - Passive measures – conductive foil, conductive 3d printing material
        - Active measures – airflow
        - Air flow in the space between the sensors and the subject’s head
        - Evaluate TCPoly sensor heat sinks using OPMs instead of resistor model with FLIR

 
- **MuCoil hardware:**

    - Integration of QuSpin OPMs for calibration of MuCoils (partially finished)
        - Currently, 2 QuSpin wires are disconnected from the breakout board, probably caused by moving the breakout board.
    - Active field cancellation with MuCoils
    - Standardization of MuCoil placement (i.e. markers on the floor)
    
- **OPM software:**

    - Program OPM acquisition interface using APIs
    - Use LSL interface for acquisition display and real-time analysis. Requirements:
        - [FieldLine LSL module](https://github.com/jzerfowski/fieldline_lsl)
        - [FieldLine API](https://github.com/juangpc/fieldline-opm-client)
        - [pylsl](https://pypi.org/project/pylsl/)      
    - Localization of sensor array in head coordinate system
    - 1st gradient response synthesis

- **Galileo**
 
    - Write and test somatosensory stimulation task using the Galileo system
 
- **Calibration**

    - [ ] Verify fitting algorithm with new OPMcal data
    - [ ] Collect longer datasets at reduced coil currents
    - [ ] Collect datasets with and without additional spacing between array and calibrator
    - [ ] Test different fitting methods (L-M, simplex, beamformer scan, etc.) for performance and accuracy
    - [ ] Test OPMcal using theoretical predictions with added noise (done, but repeat at every iteration of the software as a sanity check)
    - [ ] Compare field maps from MtoB, LtoB, and computational methods with measured fieldmaps from the CTF MEG and from the OPMs
    - [ ] Incorporate crosstalk correction
    - [ ] Integrate over the OPM vapor cell
    - [ ] Created table for 1st-gradient response synthesis
    - [ ] Create sensor frame centered on references that can be transformed to the head frame.
  
- **Anticipated manuscripts**

    - Simulated performance in the presence of multiple independent sources. (in progress, submission anticipated soon)
    - Calibration of a dense OPM array
    - Validation of a dense OPM array performance using somatotopy
 
 
 

