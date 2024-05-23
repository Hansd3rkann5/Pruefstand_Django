import itertools
import time
import crcmod
import struct
import crc16 as c16
from crc import *


class crc:

    order = ""
    polynom = ""
    init = ""
    xor = ""
    reflect0 = False
    reflect1 = False
    direct = False
    data = ""
    result = ""

    def __init__(self):
        pass

    def setCRC8(self):
        """
        Sets the CRC Calculation tothe CRC8. The values are set as follow:
        Width = 8 bits
        Truncated Polynomial = 0x01
        Initial Value = 0x0000
        Data is reflected
        Output is reflected
        No XOR is performed on the output CRC
        """
        self.reflect1 = True
        self.direct = True
        self.reflect0 = True
        self.init = "0"
        self.xor = "0"
        self.order = "8"
        self.polynom = "1"

    def setCRCccitt(self):
        """
        Sets the CRC Calculation tothe CRC16-CCITT. The values are set as follow:
        Width = 16 bits
        Truncated Polynomial = 0x1021
        Initial Value = 0xFFFF
        Data is not reflected
        Output is not reflected
        No XOR is performed on the output CRC
        """
        self.order = "16"
        self.polynom = "1021"
        self.init = "ffff"
        self.xor = ""
        self.reflect0 = False
        self.reflect1 = False
        self.direct = True

    def setCRC16(self):
        """
        Sets the CRC Calculation to the CRC16. The values are set as follow:
        Width = 16 bits
        Truncated Polynomial = 0x8005
        Initial Value = 0x0000
        Data is reflected
        Output is reflected
        No XOR is performed on the output CRC
        """
        self.order = "16"
        self.polynom = "8005"
        self.init = "0"
        self.xor = "0"
        self.reflect0 = True
        self.reflect1 = True
        self.direct = True

    def setCRC32(self):
        """
        Sets the CRC Calculation to the CRC32. The values are set as follow:
        Width = 32 bits
        Truncated Polynomial = 0x4c11db7
        Initial Value = 0xffffffff
        Data is reflected
        Output is reflected
        XOR is performed on the output CRC
        """
        self.order = "32"
        self.polynom = "4c11db7"
        self.init = "ffffffff"
        self.xor = "ffffffff"
        self.reflect0 = True
        self.reflect1 = True
        self.direct = True

    def compute(self):
        """
        Computes the CRC with the selected values and store the result at self.result
        """
        i = 0
        j = 0
        k = 0
        bit = False
        datalen = 0
        lenght = 0
        flag = False
        counter = 0
        c = 0
        crc = ["", "", "", "", "", "", "", "", ""]
        mask = ["", "", "", "", "", "", "", ""]
        init = ["", "", "", "", "", "", "", ""]
        hexnum = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"]

        data = ""
        order = ""
        polynom = ["", "", "", "", "", "", "", ""]
        xor = ["", "", "", "", "", "", "", ""]

        # Check if parameters are present
        if self.order == "" or self.polynom == "" or self.init == "" or self.xor == "":
            raise Exception("Invalid Parameters")

        # Convert CRC Order
        order = int(self.order, 10)
        if order < 1 or order > 64:
            raise Exception("CRC order must be between 1 and 64")

        #Convert CRC Polynom
        polynom = self.convertentry(self.polynom, order)
        if polynom[0] < 0:
            raise Exception("Invalid CRC polynom")

        if not(polynom[7] & 1):
            raise Exception("CRC polynom LSB must be set")

        init = self.convertentry(self.init, order)
        if init[0] < 0:
            raise Exception("Invalid initial value")

        # Convert CRC XOR value
        xor = self.convertentry(self.xor, order)
        if xor[0] < 0:
            raise Exception("Invalid XOR value")

        # Generate bit mask
        counter = order
        for i in range(7, -1, -1):
            if counter >= 8:
                mask[i] = 255
            else:
                mask[i] = (1 << counter) - 1
            counter -= 8

            if counter < 0:
                counter = 0
        crc = init

        if self.direct:  # Non Direct -> Direct
            crc.append(0)

            for i in range(0, order):
                bit = crc[7-((order-1) >> 3)] & (1 << ((order-1) & 7))
                for k in range(0, 8):
                    crc[k] = ((crc[k] << 1) | (crc[k+1] >> 7)) & mask[k]
                    if bit:
                        crc[k] ^= polynom[k]

        data = self.data
        datalen = len(data)
        lenght = 0  # number of data bytes

        crc.append(0)

        for i in range(0, datalen):
            c = ord(data[i])
            if data[i] == '%':
                if i > datalen-3:
                    raise Exception("Invalid data Sequence")
                try:
                    ch = int(data[++i], 16)
                except ValueError:
                    raise Exception("Invalid data Sequence")
                c = (c & 15) | ((ch & 15) << 4)

            # perform revin
            if self.reflect0:
                c = self.reflectByte(c)

            # rotate one data byte including crcmask
            for j in range(0,8):
                bit = 0
                if crc[7-((order-1) >> 3)] & (1 << ((order-1) & 7)):
                    bit = 1
                if c & 0x80:
                    bit ^= 1
                c <<= 1

                for k in range(0,8):  # Rotate all (max 8) crc bytes
                    crc[k] = ((crc[k] << 1) | (crc[k+1] >> 7)) & mask[k]
                    if bit:
                        crc[k] ^= polynom[k]
                lenght += 1
        # perform revout
        if self.reflect1:
            crc = self.reflect(crc, order, 0)

        # perform xor value
        for i in range(0, 8):
            crc[i] ^= xor[i]

        # write results
        self.result = ""
        flag = 0

        for i in range(0,8):
            actchar = crc[i] >> 4
            if flag or actchar:
                self.result += hexnum[actchar]
                flag=1
            actchar = crc[i] & 15
            if flag or actchar or i == 7:
                self.result += hexnum[actchar]
                flag = 1

    def revpoly(self):
        """
        Reverses the polynom
        """
        # reverses poly
        polynom = ["", "", "", "", "", "", "", "", ""]
        order = 0
        actchar = ""
        flag = False
        hexnum = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"]

        self.result = ""

        #  convert crc order
        try:
            order = int(self.order, 10)
        except ValueError:
            raise Exception("CRC order must be between 1 and 64")

        # convert crc polynom
        polynom = self.convertentry(self.polynom, order)
        if polynom[0] < 0:
            raise Exception("Invalid CRC polynom")

        # check if polynom is valid
        if not (polynom[7] & 1):
            raise Exception("CRC polynom LSB must be set")

        # compute reversed polynom

        polynom = self.reflect(polynom, order, 1)

        # write result

        self.polynom = ""

        flag = 0

        for i in range(0, 8):
            actchar = polynom[i] >> 4
            if flag or actchar:
                self.polynom += hexnum[actchar]
                flag = 1

            actchar = polynom[i] & 15
            if flag or actchar or i == 7:
                self.polynom += hexnum[actchar]
                flag = 1

    def reflectByte(self, inbyte):
        """
        Reflects a byte
        :param inbyte: input byte
        :return: reflected input byte
        """
        outbyte = 0
        i = 0x01
        j = 0x80

        while j != 0:
            if inbyte & i:
                outbyte |= j
            i <<= 1
            j>>=1
        return outbyte

    def reflect(self, crc, bitnum, startLSB):
        """
        Reflect a number of bits starting a the lowest bit defined by startLSB
        :param crc: the current crc hash
        :param bitnum: the number of bits to reflect
        :param startLSB: the index of the the LSB
        :return: returns a crc with the reflected bits
        """
        # reflect bitnum bits starting at lowest bit = startLSB
        i = 0
        j = 0
        k = 0
        iw = 0
        jw = 0
        bit = 0

        while k+startLSB < bitnum-1-k:
            iw = 7-((k+startLSB) >> 3)
            jw = 1 << ((k+startLSB) & 7)
            i = 7-((bitnum-1-k) >> 3)
            j = 1 << ((bitnum-1-k) & 7)

            bit = crc[iw] & jw
            if crc[i] & j:
                crc[iw] |= jw
            else:
                crc[iw] &= (0xff-jw)
            if bit:
                crc[i] |= j
            else:
                crc[i] &= (0xff-j)

            k += 1
        return crc

    def convertentry(self, input, order):
        """
        Converts from a ASCII value to another base value
        :param input: string input value
        :param order: base order
        :return:
        """
        # convert from ascii to hexadecimal value
        lenght = 0
        actchar = 0
        polynom = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        brk = [-1, 0, 0, 0, 0, 0, 0, 0]

        #convert crc value into byte sequence
        input = list(input)
        lenght = len(input)
        for i in range(0, lenght):
            try:
                actchar = int(input[i], 16)
            except ValueError:
                return brk
            actchar &=15
            for j in range(0, 8):
                polynom[j] = ((polynom[j] << 4) | (polynom[j+1] >> 4 )) & 255
            polynom[7] = ((polynom[7] << 4) | actchar) & 255

        # compute and check crc order
        count = 64
        for i in range(0, 8):
            j = 0x80
            while j > 0:
                if polynom[i] & j:
                    break
                count -= 1
                j >>= 1
            if polynom[i] & j:
                break
        if count > order:
            return brk
        return polynom

cmd = [0x03, 0x71, 0x00, 0x00, 0x00]

table1 = [
0x0000, 0x1189, 0x2312, 0x329b, 0x4624, 0x57ad, 0x6536, 0x74bf, 
0x8c48, 0x9dc1, 0xaf5a, 0xbed3, 0xca6c, 0xdbe5, 0xe97e, 0xf8f7, 
0x1081, 0x0108, 0x3393, 0x221a, 0x56a5, 0x472c, 0x75b7, 0x643e, 
0x9cc9, 0x8d40, 0xbfdb, 0xae52, 0xdaed, 0xcb64, 0xf9ff, 0xe876, 
0x2102, 0x308b, 0x0210, 0x1399, 0x6726, 0x76af, 0x4434, 0x55bd, 
0xad4a, 0xbcc3, 0x8e58, 0x9fd1, 0xeb6e, 0xfae7, 0xc87c, 0xd9f5, 
0x3183, 0x200a, 0x1291, 0x0318, 0x77a7, 0x662e, 0x54b5, 0x453c, 
0xbdcb, 0xac42, 0x9ed9, 0x8f50, 0xfbef, 0xea66, 0xd8fd, 0xc974, 
0x4204, 0x538d, 0x6116, 0x709f, 0x0420, 0x15a9, 0x2732, 0x36bb, 
0xce4c, 0xdfc5, 0xed5e, 0xfcd7, 0x8868, 0x99e1, 0xab7a, 0xbaf3, 
0x5285, 0x430c, 0x7197, 0x601e, 0x14a1, 0x0528, 0x37b3, 0x263a, 
0xdecd, 0xcf44, 0xfddf, 0xec56, 0x98e9, 0x8960, 0xbbfb, 0xaa72, 
0x6306, 0x728f, 0x4014, 0x519d, 0x2522, 0x34ab, 0x0630, 0x17b9, 
0xef4e, 0xfec7, 0xcc5c, 0xddd5, 0xa96a, 0xb8e3, 0x8a78, 0x9bf1, 
0x7387, 0x620e, 0x5095, 0x411c, 0x35a3, 0x242a, 0x16b1, 0x0738, 
0xffcf, 0xee46, 0xdcdd, 0xcd54, 0xb9eb, 0xa862, 0x9af9, 0x8b70, 
0x8408, 0x9581, 0xa71a, 0xb693, 0xc22c, 0xd3a5, 0xe13e, 0xf0b7, 
0x0840, 0x19c9, 0x2b52, 0x3adb, 0x4e64, 0x5fed, 0x6d76, 0x7cff, 
0x9489, 0x8500, 0xb79b, 0xa612, 0xd2ad, 0xc324, 0xf1bf, 0xe036, 
0x18c1, 0x0948, 0x3bd3, 0x2a5a, 0x5ee5, 0x4f6c, 0x7df7, 0x6c7e, 
0xa50a, 0xb483, 0x8618, 0x9791, 0xe32e, 0xf2a7, 0xc03c, 0xd1b5, 
0x2942, 0x38cb, 0x0a50, 0x1bd9, 0x6f66, 0x7eef, 0x4c74, 0x5dfd, 
0xb58b, 0xa402, 0x9699, 0x8710, 0xf3af, 0xe226, 0xd0bd, 0xc134, 
0x39c3, 0x284a, 0x1ad1, 0x0b58, 0x7fe7, 0x6e6e, 0x5cf5, 0x4d7c, 
0xc60c, 0xd785, 0xe51e, 0xf497, 0x8028, 0x91a1, 0xa33a, 0xb2b3, 
0x4a44, 0x5bcd, 0x6956, 0x78df, 0x0c60, 0x1de9, 0x2f72, 0x3efb, 
0xd68d, 0xc704, 0xf59f, 0xe416, 0x90a9, 0x8120, 0xb3bb, 0xa232, 
0x5ac5, 0x4b4c, 0x79d7, 0x685e, 0x1ce1, 0x0d68, 0x3ff3, 0x2e7a, 
0xe70e, 0xf687, 0xc41c, 0xd595, 0xa12a, 0xb0a3, 0x8238, 0x93b1, 
0x6b46, 0x7acf, 0x4854, 0x59dd, 0x2d62, 0x3ceb, 0x0e70, 0x1ff9, 
0xf78f, 0xe606, 0xd49d, 0xc514, 0xb1ab, 0xa022, 0x92b9, 0x8330, 
0x7bc7, 0x6a4e, 0x58d5, 0x495c, 0x3de3, 0x2c6a, 0x1ef1, 0x0f78, 
]

table2 = [
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7, 0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6, 0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485, 0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4, 0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
        0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823, 0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
        0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12, 0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
        0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41, 0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
        0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70, 0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
        0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F, 0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E, 0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D, 0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C, 0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB, 0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
        0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A, 0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
        0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9, 0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
        0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8, 0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
]
_sizeToTypeCode = {}

for typeCode in 'B H I L Q'.split():
    size = {1:8, 2:16, 4:32, 8:64}.get(struct.calcsize(typeCode),None)
    if size is not None and size not in _sizeToTypeCode:
        _sizeToTypeCode[size] = '256%s' % typeCode

_sizeToTypeCode[24] = _sizeToTypeCode[32]

config = Configuration(
  width=16,
  polynomial=0x1021,
  init_value=0xFFFF,
  final_xor_value=0x00,
  reverse_input=True,
  reverse_output=False,
)

config = Configuration(width=16, polynomial=11021, init_value=0, final_xor_value=65535, reverse_input=False, reverse_output=False)
print(hex(Calculator(config).checksum(bytes(cmd))))

crc16,tbl = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF)
#print(hex(crc16("0x0371000000".encode(), table= struct.pack(_sizeToTypeCode[16], *CRCTable))))
#B84B

test_data = [
  b"0371000000",
]

def crc16(data: bytes):
    '''
    CRC-16 (CCITT) implemented with a precomputed lookup table
    '''
    table = table1
    
    crc = 0xFFFF
    for byte in data:
        crc = (crc << 8) ^ table[(crc >> 8) ^ byte]
        crc &= 0xFFFF                                   # important, crc must stay 16bits all the way through
    return crc
  
print(hex(crc16(cmd)))
#print(c16.crc16xmodem(b'1101110001000000000000000000000000'))

crccalc = crc()
crccalc.setCRCccitt()
crccalc.data = b'01011' 
#crccalc.compute()
print(crccalc.result)

my_hexdata = "1a"

scale = 16 ## equals to hexadecimal

num_of_bits = 10

print(bin(int(my_hexdata, scale))[2:].zfill(num_of_bits))