#! /usr/bin/env python

import sys
import numpy as np
from numpy import sin, pi
import matplotlib.pyplot as plt
from time import time
from filters import filt_p, cheby2
from sensors import sens_p
from param import Param, getParam

p = Param()
p.registryMerge(filt_p)
p.registryMerge(sens_p)

try:
    p = getParam(p)
except Exception as msg:
    print(msg)
    sys.exit(1)

p.enableLogging()
p.logParam()

exit()

# Make a signal that is the sum of two sine waves sampled at 1 kHz.

s = 2   # seconds
srate = 1000
nsamp = int(s * srate)

t = np.linspace(0, s, nsamp + 1)
xlow = sin(2 * pi * 16 * t)         # a signal in the passband
xhigh = sin(2 * pi * 27 * t)        # a signal in the stopband
x = xlow + xhigh

# Make a filter.

cutoff = 25
N = 10
dB = 80

filt = cheby2(1, cutoff, N, dB, fs=srate)

# Filter an array one sample at a time.

y = np.zeros(len(x))
t0 = time()
for i in range(len(x)):
    y[i] = filt([x[i]])
print("{:.3g} ms".format((time() - t0) / len(x) * 1000))

plt.subplot(411)
plt.plot(t, xlow)
plt.subplot(412)
plt.plot(t, xhigh)
plt.subplot(413)
plt.plot(t, x)
plt.subplot(414)
plt.plot(t, xlow, t, y)
plt.show()

