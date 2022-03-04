"""This module contains functions for dealing with groups of sensors,
and using parameter files for specifying such groups."""

import time
from param import Param, propObj, Filename

__all__ = ['sens_p', 'slist2clist', 'slist2sdict', 'getIndArrays']

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
