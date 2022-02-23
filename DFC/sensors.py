"""This module contains functions for dealing with groups of sensors.
In particular, using parameter files for specifying such groups."""

from fieldline_api.fieldline_service import FieldLineService
from param import Param, propObj, Filename

def getSensorInfo(ip_list, closedLoop=True):
    """
    This function grabs basic information from the setup:
    - chassis ID
    - channel names (with the open loop [:28]/closed loop [:50] indicator)
    - calibration values
    """
    print("[getSensorInfo]")

    if closedLoop:
        suffix = ':50'
    else:
        suffix = ':28'

    sensID = []
    ch_names = []
    calib = []
    with FieldLineService(ip_list) as service:
        sensors = service.load_sensors()        # get all known sensors
        print(sensors)
        chassID = list(sensors.keys())

        for c in chassID:
            for s in sensors[c]:
                sensID.append((c, s))
                ch_names.append(service.hardware_state.get_sensor(c, s).name + suffix)

        for ch in ch_names:
            cv = service.get_calibration_value(ch)
            if type(cv) == dict:
                calib.append(cv['calibration'])
            else:
                print(ch, "has no calibration value")
                calib.append(1)

    return chassID, sensID, ch_names, calib


# Create a custom property object to parse sensor groups.

# A sensor is specified by a chassis number CC and a sensor number SS
# with CC:SS. A group of sensors is a comma or space separated list.
# Internally a sensor group is a list of tuples, [(CC, SS), ...]

class SList(propObj):
    "Store a list of sensors. This can be specified multiple times."

    def _set(self, p, val, cmdLine=False):
        slist = []
        l = self._get(p)    # see if already set
        if l:
            slist = l

        # make a new list with no commas
        vals = []
        for v in val:
            l = v.split(',')
            for name in l:
                name = name.strip()
                if len(name) == 0:  # val might have "00:00, 01:00, ..."
                    continue
                vals.append(name)

        n = 0
        ok = True
        for v in vals:
            try:
                c, s = v.split(':')
                c = int(c)
                s = int(s)
                t = (c, s)
                if t not in slist:  # ignore dups
                    slist.append(t)
            except:
                # if we're on the command line, an error means stop processing
                if not cmdLine:
                    raise ValueError(f"{self._name}: invalid sensor name '{name}'")
                ok = False
            if not ok:
                break
            n += 1

        p.set(self._name, slist)
        return n

    def _print(self, name, v, file):
        print(self._name, end = ' ', file = file)
        for c, s in v:
            print(f"{c:02d}:{s:02d}", end = ' ', file = file)
        print(file = file)

# Define the parameters that can appear in the parameter file to
# specify which sensors are references, primaries, or ADCs.

# @@@ fif2ctf could use this parameter file instead of the jig.def file.

sens_p = Param()
sens_p.mkDesc('JigDef', 'j', Filename(), arghelp="JIGFILE", default="jig.def",
    help="The name of a file to store the jig layout.")
sens_p.mkDesc('RefList', None, SList(), listValue=True, arghelp="SENSORLIST",
    help="A list of reference sensors.", default=[])
sens_p.mkDesc('PrimList', None, SList(), listValue=True, arghelp="SENSORLIST",
    help="The list of primary sensors.", default=[])
sens_p.mkDesc('ADCList', None, SList(), listValue=True, arghelp="SENSORLIST",
    help="A list of ADC channels.", default=[])

#def writeJigDef(p):
#    "Given the parameter object with the sensor lists, write the jig.def file."
#    pass
