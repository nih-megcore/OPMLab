"""This module contains functions for dealing with groups of sensors,
using parameter files for specifying such groups, and service related
calls."""

import logging
from fieldline_api.fieldline_service import FieldLineService
from param import Param, propObj, Filename

# So we can 'from sensors import *'

__all__ = ['sens_p', 'slist2clist', 'slist2sdict', 'getIndArrays',
    'getSensors', 'getSensorInfo', 'getCoeffs', 'call_done',
    'restart_sensors', 'coarse_zero', 'fine_zero']

# Create a custom property object to parse sensor groups.

# A sensor is specified by a chassis number CC and a sensor number SS
# with CC:SS. A group of sensors is a comma or space separated list.
# Internally a sensor group is a list of tuples, [(CC, SS), ...]

class SList(propObj):
    """Store a list of sensors. This can be specified multiple times.
    The syntax CC:* is allowed, and expands to all 16 sensors."""

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
                if len(name) == 0:  # val might have "00:01, 00:02, ..."
                    continue
                vals.append(name)

        n = 0
        ok = True
        for v in vals:
            try:
                c, s = v.split(':')
                c = int(c)
                if s == '*':
                    s = range(1, 17)
                    slist.extend([(c, x) for x in s])
                else:
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

def slist2clist(slist):
    "Return a list of the chassis numbers found in a sensor list"

    l = []
    for c, s in slist:
        if c not in l:
            l.append(c)
    return l

def slist2sdict(slist):
    "Convert a sensor list [(c, s), ...] into a sensor dict {c: [s1, s2, ...], ...}"

    sdict = {}
    for c, s in slist:
        if not sdict.get(c):
            sdict[c] = []
        sdict[c].append(s)
    return sdict

def getIndArrays(sensID, refList, primList):
    """Return a list of the (c, s) pairs we are actually using, from sensID,
    along with the reference and primary indices into sensID."""

    slist = refList + primList
    for c, s in slist:
        if (c, s) not in sensID:
            raise RuntimeError(f"The specified sensor {c:02d}:{s:02d} is not available.")

    refInd = []
    for c, s in refList:
        refInd.append(sensID.index((c, s)))

    primInd = []
    for c, s in primList:
        primInd.append(sensID.index((c, s)))

    return slist, refInd, primInd

# Service related calls.

def getSensors(ip_list):
    "Get the list of all known (chassis, sensor) pairs."

    sensors = []
    with FieldLineService(ip_list) as service:
        sdict = service.load_sensors()        # get all known sensors
        print('[getSensors]', sdict)
        chassID = list(sdict.keys())

        for c in chassID:
            for s in sdict[c]:
                sensors.append((c, s))

    return sensors

def getSensorInfo(ip_list, sdict, closedLoop=True):
    """
    This function gets post-zeroing information from the setup:
    - channel names (with the open loop [:28]/closed loop [:50] indicator)
    - calibration values
    """

    if closedLoop:
        suffix = ':50'
    else:
        suffix = ':28'

    ch_names = {}
    calib = {}
    with FieldLineService(ip_list) as service:
        chassID = list(sdict.keys())
        for c in chassID:
            for s in sdict[c]:
                ch = service.hardware_state.get_sensor(c, s).name + suffix
                ch_names[(c, s)] = ch
                cv = service.get_calibration_value(ch)
                if type(cv) == dict:
                    calib[(c, s)] = cv['calibration']

        if len(calib) == 0:
            logging.warn("no calibration values")

    return ch_names, calib

def getCoeffs(ip_list, sdict):
    """
    get coarse zero or fine zero field offset values
    """
    with FieldLineService(ip_list) as service:
        chassID = list(sdict.keys())
        field_coeffs = []
        for c in chassID:
            for s in sdict[c]:
                field_coeffs.append(service.get_fields(c, s))

    return field_coeffs

# Generic "done" callback

done = False
def call_done():
    global done
    done = True

def restart_sensors(ip_list, sdict, closedLoop=True):
    global done

    try:
        with FieldLineService(ip_list) as service:
            done = False
            print("Doing sensor restart")
            service.restart_sensors(sdict,
                on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished restart'),
                on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

            if closedLoop:
                # Make sure closed loop is set
                service.set_closed_loop(True)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))

def coarse_zero(ip_list, sdict):
    global done

    try:
        with FieldLineService(ip_list) as service:
            done = False
            print("Doing coarse zero")
            service.coarse_zero_sensors(sdict,
                on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished coarse zero'),
                on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))

    # return the field coefficients

    return getCoeffs(ip_list, sdict)

def fine_zero(ip_list, sdict):
    global done

    try:
        with FieldLineService(ip_list) as service:
            done = False
            print("Doing fine zero")
            service.fine_zero_sensors(sdict,
                on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
                on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
                on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))

    # return the field coefficients

    return getCoeffs(ip_list, sdict)

