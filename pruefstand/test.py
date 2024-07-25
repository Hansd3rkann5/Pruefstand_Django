import crc16
import time
import crcmod.predefined
from binascii import unhexlify

strung = ''
crc = list('0300000000')
for i in range(0, 2, 1):
    for j in range(256):
        crc[4:6] = hex(i)[2:].zfill(2).upper()
        crc[2:4] = hex(j)[2:].zfill(2).upper()
        #strung+='0' + str(crc[0]) + str(crc[1]) + str(crc[2]) + '0' + str(crc[3]) + '0' + str(crc[4])
        s = unhexlify(strung.join(crc))
        crc16 = crcmod.predefined.Crc('X25')
        crc16.update(s)
        crc[10:12] = crc16.hexdigest()[:2]
        crc[12:14] = crc16.hexdigest()[2:]
        crc[14:16] = '00'
        strung = strung.join(crc)
        for r in range(1, 9, 1):
            print(hex(int(strung[r*2-2:r*2], 16))[2:], sep=' ', end='', flush=True)
            time.sleep(0.5)
        print('')
        #print(f'{strung[:2]} {strung[2:4]} {strung[4:6]} {strung[6:8]} {strung[8:10]} {strung[10:12]} {strung[12:14]} {strung[14:]}')
        #print('\n')
        strung=''
        crc = list('0300000000')
