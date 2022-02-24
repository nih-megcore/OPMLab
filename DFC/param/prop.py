"""Property objects are attributes that can do error checking when
their value is set, and other magic."""

import os

class propObj(object):
    """Property object for the Param class. Base class for
    fancier types that override the _get or _set methods."""

    def __init__(self, name = None, **kw):
        super().__init__()
        self._name = None           # inactive
        self._kw = kw
        self._default = kw.get('default')

    def _setName(self, name):       # set to activate, before use
        self._name = name

    def _getNargs(self, n, args):
        """Get the list of args, return n of them."""

        if len(args) < n:
            raise ValueError(f"{self._name} must have {n} value{'' if n == 1 else 's'}")
        return args[:n]

    def _get(self, p):              # p is the param object
        return p.get(self._name, self._default)

    def _set(self, p, val):         # typically overriden
        p.set(self._name, val)

    def _del(self, p):
        pass

class Bool(propObj):
    "Store a boolean, defaults to True."

    def _set(self, p, val):
        v = True
        if len(val) >= 1:
            s = val[0].lower()
            if s[0] != '-':
                if s[0] == 'f':
                    v = False
                elif s[0] != 't':
                    raise ValueError(f"{self._name}: invalid bool '{val[0]}'")
        p.set(self._name, v)
        return 0

class Str(propObj):
    "Store a string."

    def _set(self, p, val):
        args = self._getNargs(1, val)
        val = args[0]
        if type(val) != str:
            raise ValueError(f"{self._name}: {val} is not a string")
        p.set(self._name, val)
        return 1

class Int(propObj):
    "Store an integer."

    def _set(self, p, val):
        args = self._getNargs(1, val)
        try:
            val = int(args[0])
        except:
            raise ValueError(f"{self._name}: {args[0]} is not an integer")
        p.set(self._name, val)
        return 1

class Float(propObj):
    "Store a float."

    def _set(self, p, val):
        args = self._getNargs(1, val)
        try:
            val = float(args[0])
        except:
            raise ValueError(f"{self._name}: {args[0]} is not a float")
        p.set(self._name, val)
        return 1

class Float2(propObj):
    "A pair of floats."

    def _set(self, p, val):
        args = self._getNargs(2, val)
        try:
            a, b = [float(x) for x in args]
        except:
            raise ValueError(f"{self._name}: arguments must be a pair of floats")
        p.set(self._name, (a, b))
        return 2

"""
class FloatList(propObj):
    "Store a list of floats."

    def _set(self, p, val):
        print(f'FloatList {val}')

        l = p.get(self._name)
        if l is None:
            l = []
            p.set(self._name, l)
        n = len(l)

        t = type(val)
        if t == int or t == float:
            val = [val]
        if type(val) != list or len(val) == 0:
            raise ValueError(f"{self._name} must have a value")

        for v in val:
            try:
                v = float(v)
                l.append(v)
            except:
                break

        p.set(self._name, l)
        return len(l) - n
"""

class FreqBand(propObj):
    "Low and high bandstops in Hz."

    def _set(self, p, val):
        args = self._getNargs(2, val)
        ok = True
        try:
            lo, hi = [float(x) for x in args]
        except:
            ok = False
        if not ok or not (0 <= lo < hi):
            raise ValueError(f"{self._name}: values must be 0 <= low < high")
        p.set(self._name, (lo, hi))
        return 2

# @@@ only difference here is the error check/message

class TimeWin(propObj):
    "Time window in seconds."

    def _set(self, p, val):
        args = self._getNargs(2, val)
        ok = True
        try:
            t0, t1 = [float(x) for x in args]
        except:
            ok = False
        if not ok or not (t0 < t1):
            raise ValueError(f"{self._name}: must have t0 < t1")
        p.set(self._name, (t0, t1))
        return 2

class Filename(propObj):
    "Store a filename, optionally check for existence."

    def _set(self, p, val):
        args = self._getNargs(1, val)
        name = args[0]
        if type(name) != str:
            raise ValueError(f"{self._name}: argument not a string '{name}'")
        if self._kw.get('mustExist'):
            ok = True
            if not os.access(name, os.F_OK):
                ok = False
                # Try again with an optional extension.
                ext = self._kw.get('ext')
                if ext:
                    name = name + os.path.extsep + ext
                    if os.access(name, os.F_OK):
                        ok = True
                if not ok:
                    raise ValueError(f"{self._name}: file not found '{name}'")
        p.set(self._name, name)
        return 1

class Dirname(propObj):
    "Store a directory name, optionally check for existence and/or create."

    def _set(self, p, val):
        args = self._getNargs(1, val)
        name = args[0]
        if type(name) != str:
            raise ValueError(f"{self._name}: argument not a string '{name}'")
        if name[-1] == os.path.sep:     # strip a trailing /
            name = name[:-1]
        if not os.access(name, os.F_OK):
            if self._kw.get('create'):
                os.mkdir(name)
            elif self._kw.get('mustExist'):
                raise ValueError(f"{self._name}: directory not found '{name}'")
        p.set(self._name, name)
        return 1
