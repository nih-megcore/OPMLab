#! /usr/bin/env python

import os
import struct
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np

FIFO = "_fifo"

win = pg.GraphicsWindow()
win.setWindowTitle('Scrolling Plots')

# 4x4 array of plots (but kept in a linear list)

p = []
for i in range(4):
    for j in range(4):
        p.append(win.addPlot())
        win.nextCol()
    win.nextRow()

data = np.zeros((16, 1000))
curve = [None] * 16
for c in range(16):
    curve[c] = p[c].plot(data[c])

# Read from this fifo

try:
    os.mkfifo(FIFO)
except FileExistsError:
    pass
fifo = os.open(FIFO, os.O_RDONLY)

# Packed format for one sample

FMT = "=16f"
SIZE = struct.calcsize(FMT)

def get(nsamp):
    global data

    data = np.roll(data, -nsamp, axis = 1)
    for i in range(nsamp):
        samp = os.read(fifo, SIZE)
        if len(samp) != 0:
            data[:, i - nsamp] = struct.unpack(FMT, samp)

def update():
    get(50)
    for c in range(16):
        curve[c].setData(data[c])

timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(1)

QtGui.QApplication.instance().exec_()
