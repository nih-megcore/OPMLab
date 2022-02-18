"""This module implements filters for use in filtering OPM outputs.

    Filter types:
        ema     Exponential moving average
        cheby2  Chebyshev type II lowpass
        nofilt  No filter
"""

import numpy as np
from scipy import signal
from param import Param, propObj

# Create a custom property object to parse the filter spec.

# THIS ISN'T USED YET

# Because the filter specification is complex, I might change how it is parsed to
# use a format such as
#
#   cheby2 cutoff=25 order=10 dB=80
# or
#   ema tau=.01
#
# This would remove the clunky "option" processing and allow other fields, and also
# make it simpler to specify on the command line. Option processing would stop
# if something is seen that doesn't have an '='.

class Filter(propObj):
    "Store a filter specification."

    def _set(self, p, val):
        try:
            name = val[0]
            name = name.lower()
            if 'ema'.startswith(name):
                name = 'e'
            elif 'cheby2'.startswith(name):
                name = 'c'
            elif 'nofilt'.startswith(name):
                name = 'n'
            else:
                raise
            if name == 'e':
                tau = float(val[1])
                r = (name, tau)
            elif name == 'c':
                cutoff = float(val[1])
                order = None                # Letting order default works best
                if len(val) > 2:            # in a file, or if the filter spec
                    order = int(val[2])     # is the last thing on the command line
                r = (name, cutoff, order)
            elif name == 'n':
                r = (name,)
        except:
            raise ValueError(f"{self._name}: bad filter type specification")

        p.set(self._name, r)
        return len(r)

# Options (command line or parameter file) used to specify the filter.

filt_p = Param()
filt_p.mkDesc('FilterType', 'f', Filter(), arghelp="FILTERSPEC", default=('e', .01),
    help="""Specify the filter and filter parameters to use.
        FILTERSPEC specifies the filter type as follows
            EMA TAU               -- Exponential moving average filter with time constant TAU
            CHEBY2 CUTOFF [ORDER] -- Chebyshev type II, CUTOFF is in Hz, ORDER is an int (default 10)
            NOFILT                -- a filter that does nothing
        The filter names may be lower case and abbreviated.""")

# END UNSED PART


class nofilt:

    def __init__(self, nChan):
        """Create a multi-channel identity function.

        Parameters:

            nChan : int
                The number of channels.
                Note that this is not part of the filter spec. All
                channels use the same type of filter.

        Returns:

            The instance returned is a callable that implements
            the filter one point at a time.
        """

        self.nChan = nChan
        self.restart()

    def restart(self):
        """Restarting the filter does nothing."""

        pass

    def __call__(self, data):
        """
        Parameter: data, a numpy array of length nChan.
        Returns: data.
        """

        return data


class ema:

    def __init__(self, nChan, tau, fs=1000):
        """Create a multi-channel exponential moving average filter.

        Parameters:

            nChan : int
                The number of channels.

            tau : float
                Time constant in seconds.

            fs : int
                Sampling rate, in Hz. Defaults to 1000.

        Returns:

            The instance that ema() returns is a callable that
            implements the filter one point at a time.
        """

        self.nChan = nChan
        self.a = np.e**(-1 / (fs * tau)) # time decay
        self.restart()

    def restart(self):
        """Restart the filter by setting the moving averages to zero."""

        self.mav = np.zeros(self.nChan)

    def __call__(self, data):
        """
        Parameter: data, a numpy array of length nChan.
        Returns: the current moving average.
        """

        a = self.a
        self.mav = a * self.mav + (1-a) * data

        return self.mav


class cheby2:

    def __init__(self, nChan, cutoff, N=10, dB=80, fs=1000, btype='lowpass'):
        """Create a multi-channel Chebyshev type II lowpass filter.

        Parameters:

            nChan : int
                The number of channels. All channels start with a zero
                state vector.

            cutoff : float
                Cutoff frequency, in Hz.

            N : int
                The order of the filter; defaults to 10.

            dB : float
                Attenuation of the filter at the cutoff frequency,
                in dB, specified as a positive number. Default 80.

            fs : int
                Sampling rate, in Hz. Defaults to 1000.

            btype : str
                Filter type. Only 'lowpass' is supported.

        Returns:

            The instance that cheby2() returns is a callable that
            implements the filter one point at a time. Example:

                filt = cheby2(3, 25)    # A 3 channel 25 Hz lowpass filter

                data = [x0, x1, x2]     # must be length 3
                y = filt(data)

                # y is now an array with the same length (3) as data
        """

        # First, get the numerator (b) and denominator (a) coefficients
        # of the filter.

        b, a = signal.cheby2(N, dB, cutoff, fs=fs, btype=btype)
        self.a = a
        self.b = b

        # Initialize nChan state vectors.

        self.nChan = nChan
        self.N = N
        self.restart()

    def restart(self):
        """Restart the filter by setting the state vectors to zero."""

        self.d = np.zeros((self.nChan, self.N))

    def __call__(self, arr):
        """
        Parameter: arr, an array of length nChan.
        Returns: a filtered array of the same length.
        """

        n = self.nChan
        N = self.N
        a = self.a
        b = self.b
        r = np.empty(n)

        # Compute the output and update the state vectors.

        for j in range(n):
            x = arr[j]
            d = self.d[j]
            y = b[0] * x + d[0]
            for i in range(N-1):
                d[i] = b[i+1] * x - a[i+1] * y + d[i+1]
            d[N-1] = b[N] * x - a[N] * y
            r[j] = y

        return r
