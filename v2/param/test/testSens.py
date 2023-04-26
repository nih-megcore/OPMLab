import logging
from param import Param, getParam, Int
from sensors import sens_p

p = Param()
p.registryMerge(sens_p)
p.mkDesc('X', None, Int())

try:
    p = getParam(p)
except Exception as e:
    print(e)

p.enableLogging()

p.log(f"X is {p.X}")

p.logParam()

logging.info("this is an info")
logging.debug("this is a debug")
logging.error("this is a test")
