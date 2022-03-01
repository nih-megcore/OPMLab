import serial

GO = bytes("\r", 'utf8')

class numato:

    def __init__(self):
        portName = "/dev/ttyACM0"

        # Open port for communication
        self.serPort = serial.Serial(portName, 19200, timeout = 1)

        # Set 'output' mode on all pins
        self.command("gpio iomask ff")  # address all pins
        self.command("gpio iodir 00")   # output mode

    def activate(coilID):
        self.command(f"gpio writeall {hex(64 + coilID)[2:]}")

    def deactivate():
        self.command("gpio writeall 00")

    def command(self, s):
        self.serPort.write(bytes(s + "\r", 'utf8'))

    def preactivate(coilID):
        "send the command but don't press enter"
        s = f"gpio writeall {hex(64 + coilID)[2:]}"
        self.serPort.write(bytes(s, 'utf8'))

    def go(self):
        self.serPort.write(GO)

    def close(self):
        self.serPort.close()
