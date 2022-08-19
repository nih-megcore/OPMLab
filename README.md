# Dynamic Field Compensation

This repository contains the software used in [Robinson et al., 2022](https://www.sciencedirect.com/science/article/pii/S1053811922006747?via%3Dihub) and was developed at the NIMH MEG Core Facility. 

Requirements:
- Dynamic Field Compensation is used with FieldLine sensors and requires their api to dynamically adjust the fields
- Setup-specific rotation matrices for reference and primary sensors (the latter saved in OPM_Axes.txt)
- Currently only working with Python 3.9 (don't use v 3.10). See DFC.yml for other requirements 
