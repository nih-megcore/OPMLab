#! /usr/bin/env python

from fieldline_api.fieldline_service import FieldLineService

ip_list = ['192.168.1.40']
with FieldLineService(ip_list) as service:
    
        sensor_dict = {0: [(1, 0, 0, 0),
                           (5, 0, 0, 0),
                           (9, 0, 0, 0)]}

        service.adjust_fields(sensor_dict)    
