import serial

GO = bytes("\r", 'utf8')

class galileo:

    def __init__(self):
        portName = "/dev/ttyUSB1"
        
        # Open port for communication
        self.serPort = serial.Serial(portName, 9600, timeout =1)

    def preactivate(self, command):
        
        """
        send the command but don't press enter
        the command can be of two kinds:
        1| single valve mode: <AV,C,P,R>Cr
        2| sequence mode: <WR,C,V1On,V1Off,V2On,V2Off,V3On,V3Off,V4On,V4Off,V5On,V5Off,V6On,V6Off,V7On,V7Off,V8On,V8Off>Cr
        where: 
        - A or W are the commands for single valve vs sequence mode, respectively
        - R is the number of times to repeat the sequence
        - C is the total cycle time for the sequence (in ms). Minimum is 200ms and it has to be larger than P
        - P is the pulse duration (in ms)
        - V is the valve number [1-8]
        - When W is used:
            - V1On is the on time for valve 1 in ms
            - V1Off is the off time for valve 1 in ms

        """        
        s = command
        self.serPort.write(bytes(s, 'utf8'))

    def go(self):
        self.serPort.write(GO)
        #self.serPort.write(bytes(command + "\r", 'utf8'))
        #print(command)
        #self.serPort.write(bytes(command,'utf8'))
        #print(self.serPort.read_all())

    def close(self):
        self.serPort.close()
