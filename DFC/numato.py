import serial

class numato:

    def __init__(self):

        portName = "/dev/ttyACM0"

        # Open port for communication
        self.serPort = serial.Serial(portName, 19200, timeout = 1)

    def setOutputMode(self):
        
        self.command("gpio iomask ff")  # address all pins
        self.command("gpio iodir 00")   # output mode

    def command(self, s):
        self.serPort.write(bytes(s + "\r", 'utf8'))

    def close(self):
        self.serPort.close()
