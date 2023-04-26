# Dynamic Field Compensation [ WIP]

The software in this repository has been developed at the NIMH MEG Core Facility. 

The version of the programs used in [Robinson et al., 2022](https://www.sciencedirect.com/science/article/pii/S1053811922006747?via%3Dihub) can be found in the /v1 directory. 

Programs in /v2 correspond to the Spring 2023 release. 

[TO DO -- ADD RELEASE NOTES FOR V2]

This code requires FieldLine's API to dynamically correct the fields measured by their OPMs. The code was developed and tested with API 0.4.3 with v2 OPMs

Requirements:
- Fieldline API >=0.4.2 [?]
- Setup-specific sensor coordinates & coordinate systems - 
- Currently only working with Python 3.9
