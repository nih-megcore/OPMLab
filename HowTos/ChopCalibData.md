# ... chop calibration data

### Necessary modules:
- mne 
- path to pyctf (pyctf was written by Tom Holroyd at MEGCore): [website](https://megcore.nih.gov/index.php?title=Pyctf)) has a program that does that called fif2ctf. Or grab latest version of the program is located on tako: git clone git@tako.nimh.nih.gov:pyctf.git 
- sinteractive on
- module load ctf/6.1.14-beta

### Steps:
1. For OPM data only (CTF data is already saved in .ds format): .fif (standard output from fieldline) --> .ds using pyctf > fif2ctf
    For a single file
    ```
    python /data/benitezandonea2/Programs/pyctf/fif2ctf/fif2ctf calibratorRun_finezero_reset1_raw.fif calibratorRun_finezero_reset1_raw.ds
    ```
    For a number of files in directory:
    ```
    for FILE in *.fif;do
        orig=${FILE%'.fif'}
        ext1="${s}.fif"
        ext2="${s}.ds"
        python /data/benitezandonea2/Programs/pyctf/fif2ctf/fif2ctf $orig$ext1 $orig$ext2
    done
    ```
2. Mark start of active coil run using threshDet_test.py (this is a modification of thresholdDetect.py)

    ```
    ds="/data/benitezandonea2/Projects/OPM_calibration/OPMcal/20211008/calibratorRun_finezero_reset1_raw.ds"
    out=./tmp/out_reset1
    python /data/benitezandonea2/Programs/pyctf/thresholdDetect/thresholdDetect.py -m start -ma 6e-12 -dt 120.5 -c Input1 $ds # -m: marker name; -ma: max amplitude? ; -dt: period of time (s); -c channel name; $ds: dataset
    ```
    At the end of thresholdDetect.py, addMarker.py script is called, which adds a "start" marker at the beginning of each active coil section

    Troubleshooting: make sure you have executable permission for addmarker.py (if not, chmod +x addMarker.py)

3. Cut data based on marker location: parsemarks -m start $ds | cut -d' ' -f2 > ./tmp/moo
4. Create a new dataset using CTFtools newD, but make sure that sampling rate and duration of data is correct
    ```
    n=0
    for t in `cat ./tmp/moo`; do
        b=`dc -e "$n 2op"`      # convert n to binary
        b=`printf "%06d" $b`    # add leading zeros
        n=$((n + 1))
        t1=`python -c "print($t + 120 - 1/1000)"`
        #newDs -filter processing.cfg -f -time $t $t1 $ds $out/${b}.ds
        newDs -f -time $t $t1 $ds $out/${b}.ds
    done
    ```

5. Make sure that cut data is correct by plotting in python using verifyThresholdDetect.py, or loading the data onto DataEditor
6. Upload data onto tako: 
    ```
        scp -r *.ds meglab@tako.nimh.nih.gov:/eon1/data/opm/20211008/calibrationRun_finezero_reset1
    ```

