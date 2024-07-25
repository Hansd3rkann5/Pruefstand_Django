import itertools
import time
import crcmod
import struct
import crc16 as c16


t0 = time.time()

p = 0
while time.time() -  t0 < 6:
    time.sleep(1)
    print(time.time() - t0)
    p+=1