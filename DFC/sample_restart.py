from fieldline_api.fieldline_service import FieldLineService
from pycore.hardware_state import HardwareState

import logging
import argparse
import queue
import time
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help="Include debug-level logs.")
    parser.add_argument("-i", '--ip', type=lambda x: x.split(","), help="comma separated list of IPs", required=True)
    args = parser.parse_args()

    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(threadName)s(%(process)d) %(message)s [%(filename)s:%(lineno)d]',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.DEBUG if args.verbose else logging.ERROR,
        handlers=[stream_handler]
    )

    ip_list = args.ip
    print(f"Connecting to IPs: {ip_list}")
    done = False
    sample_counter = 0
    def call_done():
        global done
        done = True
    try:
        
        # Restart all sensors
        with FieldLineService(ip_list) as service:
            done = False
            # Get dict of all the sensors
            sensors = service.load_sensors()
            #sensors = {0: [1,5,9]}
            print(f"Got sensors: {sensors}")
            # Make sure closed loop is set
            service.set_closed_loop(True)
            print("Doing sensor restart")
            # Do the restart
            service.restart_sensors(sensors, on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished restart'), on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'), on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

        # Coarse zero all sensors
        with FieldLineService(ip_list) as service:
            done = False
            sensors = service.load_sensors()
            #sensors = {0: [1,5,9]}
            print(f"Got sensors: {sensors}")
            time.sleep(2)
            print("Doing coarse zero")
            service.coarse_zero_sensors(sensors, on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished coarse zero'), on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'), on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)

        # Fine zero all sensors
        with FieldLineService(ip_list) as service:
            done = False
            sensors = service.load_sensors()
            #sensors = {0: [1,5,9]}
            print(f"Got sensors: {sensors}")
            print("Doing fine zero")
            service.fine_zero_sensors(sensors, on_next=lambda c_id, s_id: print(f'sensor {c_id}:{s_id} finished fine zero'), on_error=lambda c_id, s_id, err: print(f'sensor {c_id}:{s_id} failed with {hex(err)}'), on_completed=lambda: call_done())
            while not done:
                time.sleep(0.5)
        
            #def print_bz(data):
            #    global sample_counter
            #    sample_counter += 1
            #    print(str(data))
            #service.read_data(print_bz)
            service.start_adc(0)
            #start = time.time()
            #while time.time() - start < 1.0:
            #    time.sleep(0.5)
            #service.stop_adc(0)
            #service.read_data()
            #print("Read %d samples" % sample_counter)

        # Turn off all the sensors
        #with FieldLineService(ip_list) as service:
        #    sensors = service.load_sensors()
        #    service.turn_off_sensors(sensors)

        with FieldLineService(ip_list) as service:
            
            channel_dict = service.hardware_state.get_channel_dict()
            print(service.hardware_state.get_sensor(0, 1))


            print(channel_dict[ch_name] if ch_name in channel_dict else 1.0)
            #print(channel_dict)
            #sensors = {0: [1,5,9]}
          
    except ConnectionError as e:
        logging.error("Failed to connect: %s" % str(e))


