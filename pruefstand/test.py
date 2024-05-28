import crc16
import time
import crcmod.predefined
from binascii import unhexlify

strung = ''
s = unhexlify('03FE020000')
crc16 = crcmod.predefined.Crc('X25')
crc16.update(s)
print(crc16.hexdigest())
crc = list('0300000000')
for i in range(0, 2, 1):
    for j in range(256):
        crc[4:6] = hex(i)[2:].zfill(2).upper()
        crc[2:4] = hex(j)[2:].zfill(2).upper()
        #strung+='0' + str(crc[0]) + str(crc[1]) + str(crc[2]) + '0' + str(crc[3]) + '0' + str(crc[4])
        s = unhexlify(strung.join(crc))
        crc16 = crcmod.predefined.Crc('X25')
        crc16.update(s)
        #print(strung.join(crc))
        #print(crc16.hexdigest())
        #time.sleep(0.5)
        crc[10:12] = crc16.hexdigest()[:2]
        crc[12:14] = crc16.hexdigest()[2:]
        crc[14:16] = '00'
        print(strung.join(crc))
        #time.sleep(1)
        strung=''
        crc = list('0300000000')

