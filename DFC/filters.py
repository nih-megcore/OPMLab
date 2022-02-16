"""This module implements filters for use in filtering OPM outputs.

    Filter types:
        ema     Exponential moving average
        cheby2  Chebyshev type II lowpass
"""

import numpy as np
from scipy import signal


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
