# Service related calls.

import time
import logging
from fieldline.fieldline_api.fieldline_service import FieldLineService
from fieldline.pycore.hardware_state import HardwareState
from fieldline.pycore.sensor import SensorInfo, ChannelInfo
from fieldline.fieldline_api.fieldline_datatype import FieldLineSensorStatusType

done = False
def call_done():
    global done
    done = True

class FLService(FieldLineService):

    def __init__(self, ip_list):
        print("\nAcquiring FieldLine service")
        try:
            super().__init__(ip_list)
            self.open()
        except ConnectionError as e:
            logging.error("Failed to connect: %s" % str(e))

    def __del__(self):
        self.close()

    def getSensors(self):
        "Get the list of all known (chassis, sensor) pairs."

        #print("[getSensors]")
        
        sdict = self.load_sensors()     # get all known sensors
        sensors = [(c,s) for c in sdict for s in sdict[c]]
        print(f"\nFound sensors: {sensors}")
        
        return sensors

    '''
    def getSensorInfo(self, sdict, closedLoop=True):
        """
        This function gets post-zeroing information for the sensors in sdict:
        - channel names (with the open loop [:28]/closed loop [:50] indicator)
        - calibration values
        These are dicts indexed by (c, s) pairs.
        """
        print("[getSensorInfo]")
        if closedLoop:
            suffix = ':50'
            print('closedLoop')
        else:
            suffix = ':28'
            print('openLoop')

        ch_names = {}
        calib = {}                            
        
        for c in sdict:
            for s in sdict[c]:
                sens = self.hardware_state.get_sensor(c, s)
                print(sens.name)
                ch = sens.name + suffix
                ch_names[(c, s)] = ch
                cv = self.get_calibration_value(ch)
                print(ch,cv)
                
                if type(cv) == dict:
                    calib[(c, s)] = cv['calibration']

        if len(calib) == 0:
            logging.warn("no calibration values")

        return ch_names, calib
    '''
    def getCoeffs(self, sdict):
        """
        get coarse zero or fine zero field offset values
        """
        #print("[getCoeffs]")
        field_coeffs = []
        for c in sdict:
            for s in sdict[c]:
                field_coeffs.append(self.get_fields(c, s))

        return field_coeffs

    def restartSensors(self, sdict, closedLoop=True):
        global done

        done = False

        print("\nDoing sensor restart")
        self.restart_sensors(sdict,
            on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished restart'),
            on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
            on_completed=lambda: call_done())

        while not done:
            time.sleep(0.5)

        if closedLoop:
            self.set_closed_loop(True)

    def coarseZero(self, sdict):
        global done

        done = False

        print("\nDoing coarse zero")
        self.coarse_zero_sensors(sdict,
            on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished coarse zero'),
            on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
            on_completed=lambda: call_done())

        while not done:
            time.sleep(0.5)

    def fineZero(self, sdict):
        global done

        done = False

        print("\nDoing fine zero")
        self.fine_zero_sensors(sdict,
            on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'),
            on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'),
            on_completed=lambda: call_done())

        while not done:
            time.sleep(0.002)

    def get_not_ready(self):
        # find all sensors that are not ready/are off
        l = []
        for s in self.hardware_state.get_sensors():
            if s.get_color() == 9 and s.get_blink_state() == 1:
                l.append((s.chassis_id, s.sensor_id))
        
        return l
