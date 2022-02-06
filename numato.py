#! /usr/bin/env python

import sys
import serial

portName = "/dev/ttyACM0"
command = sys.argv[1]

# Open port for communication
serPort = serial.Serial(portName, 19200, timeout = 1)

# Send the command
serPort.write(bytes(command + "\r", 'utf8'))

# Close the port
serPort.close()
