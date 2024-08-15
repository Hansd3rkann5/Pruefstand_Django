## Needed Imports
from PCANBasic import *
import os
import crc16
import time
import crcmod.predefined
from binascii import unhexlify
import sys

class ManualWrite():

    # Defines
    #region

    # Sets the PCANHandle (Hardware Channel)
    PcanHandle = PCAN_USBBUS1

    # Sets the desired connection mode (CAN = false / CAN-FD = true)
    IsFD = False

    # Sets the bitrate for normal CAN devices
    Bitrate = PCAN_BAUD_500K

    # Sets the bitrate for CAN FD devices. 
    # Example - Bitrate Nom: 1Mbit/s Data: 2Mbit/s:
    #   "f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1"
    BitrateFD = b'f_clock_mhz=20, nom_brp=5, nom_tseg1=2, nom_tseg2=1, nom_sjw=1, data_brp=2, data_tseg1=3, data_tseg2=1, data_sjw=1'    
    #endregion

    # Members
    #region

    # Shows if DLL was found
    m_DLLFound = False

    #endregion

    def __init__(self):
        """
        Create an object starts the programm
        """
        self.strung = ''
        #self.crc = list('0300000000')
        self.crc = list('0140000000000000')
        self.msgCanMessage = TPCANMsg()
        self.msgCanMessage.LEN = 8
        self.msgCanMessage.MSGTYPE = PCAN_MESSAGE_EXTENDED.value
        self.ShowConfigurationHelp() ## Shows information about this sample
        self.ShowCurrentConfiguration() ## Shows the current parameters configuration

        ## Checks if PCANBasic.dll is available, if not, the program terminates
        try:
            self.m_objPCANBasic = PCANBasic()
            self.m_DLLFound = True
        except :
            print("Unable to find the library: PCANBasic.dll !")
            self.getInput("Press <Enter> to quit...")
            self.m_DLLFound = False
            return

        
        ## Initialization of the selected channel
        if self.IsFD:
            stsResult = self.m_objPCANBasic.InitializeFD(self.PcanHandle,self.BitrateFD)
        else:
            stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle,self.Bitrate)

        if stsResult != PCAN_ERROR_OK:
            print("Can not initialize. Please check the defines in the code.")
            self.ShowStatus(stsResult)
            print("")
            self.getInput("Press <Enter> to quit...")
            return

        ## Writing messages...
        print("Successfully initialized.")
        self.getInput("Press <Enter> to write...")
        strinput = "y"
        p = 1
        by = []
        self.clear()
        while strinput == "y":
            for i in range(0, 1, 1):
                for j in range(256):
                    # self.crc[4:6] = hex(i)[2:].zfill(2).upper()
                    # self.crc[2:4] = hex(j)[2:].zfill(2).upper()
                    # s = unhexlify(self.strung.join(self.crc))
                    # crc16 = crcmod.predefined.Crc('X25')
                    # crc16.update(s)
                    # self.crc[10:12] = crc16.hexdigest()[:2]
                    # self.crc[12:14] = crc16.hexdigest()[2:]
                    # self.crc[14:16] = '00'
                    self.strung = '0410'
                    self.msgCanMessage.ID = 1546
                    for r in range(1, 3, 1): 
                        self.msgCanMessage.DATA[r-1] = int(hex(int(self.strung[r*2-2:r*2], 16)),16)
                    self.msgCanMessage.LEN = 2
                    #     by.append(hex(int(self.strung[r*2-2:r*2], 16)))
                        #print(msgCanMessage.DATA[r-1])
                    print(hex(self.msgCanMessage.ID))
                    #print(self.msgCanMessage)
                    #print(f'0{by[0][1:]} {by[1][2:]} 0{by[2][2:]} 0{by[3][2:]} 0{by[4][2:]} {by[5][2:]} {by[6][2:]} 0{by[7][2:]} ')
                    print('--------------------------')
                    stsResult = self.m_objPCANBasic.Write(self.PcanHandle, self.msgCanMessage)
                    self.strung=''
                    #self.crc = list('0300000000')
                    time.sleep(0.05)
                    by = []
                    self.crc = list('0300000000')                    
                #self.crc[:2] = 
                break
            strinput = self.getInput("Do you want to write again? yes[y] or any other key to exit...", "y")
            strinput = chr(ord(strinput))

    def __del__(self):
        if self.m_DLLFound:
            self.m_objPCANBasic.Uninitialize(PCAN_NONEBUS)

    def getInput(self, msg="Press <Enter> to continue...", default=""):
        res = default
        if sys.version_info[0] >= 3:
            res = input(msg + " ")
        else:
            res = raw_input(msg + " ")
        if len(res) == 0:
            res = default
        return res

    # Main-Functions
    #region
    def WriteMessages(self, strung):
        '''
        Function for writing PCAN-Basic messages
        '''
        if self.IsFD:
            stsResult = self.WriteMessageFD()
        else:
            stsResult = self.WriteMessage(self, '0x0cf')

        ## Checks if the message was sent
        if (stsResult != PCAN_ERROR_OK):
            self.ShowStatus(stsResult)
        else:
            print("Message was successfully SENT")

    def WriteMessage(self, id, data):
        """
        Function for writing messages on CAN devices

        Returns:
            A TPCANStatus error code
        """
        ## Sends a CAN message with extended ID, and 8 data bytes
        self.msgCanMessage.ID = id
        self.msgCanMessage.DATA = data
        return self.m_objPCANBasic.Write(self.PcanHandle, self.msgCanMessage)
        for i in range(0, 2, 1):
            for j in range(256):
                crc[4:6] = hex(i)[2:].zfill(2).upper()
                crc[2:4] = hex(j)[2:].zfill(2).upper()
                s = unhexlify(strung.join(crc))
                crc16 = crcmod.predefined.Crc('X25')
                crc16.update(s)
                crc[10:12] = crc16.hexdigest()[:2]
                crc[12:14] = crc16.hexdigest()[2:]
                crc[14:16] = '00'
                print(strung.join(crc))
                strung = strung.join(crc)
                for r in range(1, 9, 1): 
                    msgCanMessage.DATA[r-1] = int(hex(int(strung[r*2-2:r*2], 16)), 16)
                    #print(msgCanMessage.DATA[r-1])
                print(f'{msgCanMessage.DATA[0]} {msgCanMessage.DATA[1]} {msgCanMessage.DATA[2]} {msgCanMessage.DATA[3]} {msgCanMessage.DATA[4]} {msgCanMessage.DATA[5]} {msgCanMessage.DATA[6]} {msgCanMessage.DATA[7]} ')
                return self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
                #print(f'{strung[:2]} {strung[2:4]} {strung[4:6]} {strung[6:8]} {strung[8:10]} {strung[10:12]} {strung[12:14]} {strung[14:]}')
        # for r in range(1, 9, 1): 
        #     msgCanMessage.DATA[i-1] = int(hex(int(strung[r*2-2:r*2], 16)), 16)
        #     pass
        # print(msgCanMessage.DATA)
        # return self.m_objPCANBasic.Write(self.PcanHandle, msgCanMessage)
    
    def check_sum(self):
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
                return strung
                print(f'{strung[:2]} {strung[2:4]} {strung[4:6]} {strung[6:8]} {strung[8:10]} {strung[10:12]} {strung[12:14]} {strung[14:]}')
                strung=''
                crc = list('0300000000')

    def WriteMessageFD(self):
        """
        Function for writing messages on CAN-FD devices

        Returns:
            A TPCANStatus error code
        """
        ## Sends a CAN-FD message with standard ID, 64 data bytes, and bitrate switch
        msgCanMessageFD = TPCANMsgFD()
        msgCanMessageFD.ID = 0x0Cf
        msgCanMessageFD.DLC = 15
        msgCanMessageFD.MSGTYPE = PCAN_MESSAGE_FD.value | PCAN_MESSAGE_BRS.value
        for i in range(64):
            msgCanMessageFD.DATA[i] = i
            pass
        return self.m_objPCANBasic.WriteFD(self.PcanHandle, msgCanMessageFD)
    #endregion

    # Help-Functions
    #region
    def clear(self):
        """
        Clears the console
        """
        if os.name=='nt':
            os.system('cls')
        else:
            os.system('clear')
        
    def ShowConfigurationHelp(self):
        """
        Shows/prints the configurable parameters for this sample and information about them
        """
        print("=========================================================================================")
        print("|                        PCAN-Basic ManualWrite Example                                  |")
        print("=========================================================================================")
        print("Following parameters are to be adjusted before launching, according to the hardware used |")
        print("                                                                                         |")
        print("* PcanHandle: Numeric value that represents the handle of the PCAN-Basic channel to use. |")
        print("              See 'PCAN-Handle Definitions' within the documentation                     |")
        print("* IsFD: Boolean value that indicates the communication mode, CAN (false) or CAN-FD (true)|")
        print("* Bitrate: Numeric value that represents the BTR0/BR1 bitrate value to be used for CAN   |")
        print("           communication                                                                 |")
        print("* BitrateFD: String value that represents the nominal/data bitrate value to be used for  |")
        print("             CAN-FD communication                                                        |")
        print("=========================================================================================")
        print("")

    def ShowCurrentConfiguration(self):
        """
        Shows/prints the configured paramters
        """
        print("Parameter values used")
        print("----------------------")
        print("* PCANHandle: " + self.FormatChannelName(self.PcanHandle))
        print("* IsFD: " + str(self.IsFD))
        print("* Bitrate: " + self.ConvertBitrateToString(self.Bitrate))
        print("* BitrateFD: " + self.ConvertBytesToString(self.BitrateFD))
        print("")

    def ShowStatus(self,status):
        """
        Shows formatted status

        Parameters:
            status = Will be formatted
        """
        print("=========================================================================================")
        print(self.GetFormattedError(status))
        print("=========================================================================================")
    
    def FormatChannelName(self, handle, isFD=False):
        """
        Gets the formated text for a PCAN-Basic channel handle

        Parameters:
            handle = PCAN-Basic Handle to format
            isFD = If the channel is FD capable

        Returns:
            The formatted text for a channel
        """
        handleValue = handle.value
        if handleValue < 0x100:
            devDevice = TPCANDevice(handleValue >> 4)
            byChannel = handleValue & 0xF
        else:
            devDevice = TPCANDevice(handleValue >> 8)
            byChannel = handleValue & 0xFF

        if isFD:
           return ('%s:FD %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handleValue))
        else:
           return ('%s %s (%.2Xh)' % (self.GetDeviceName(devDevice.value), byChannel, handleValue))

    def GetFormattedError(self, error):
        """
        Help Function used to get an error as text

        Parameters:
            error = Error code to be translated

        Returns:
            A text with the translated error
        """
        ## Gets the text using the GetErrorText API function. If the function success, the translated error is returned.
        ## If it fails, a text describing the current error is returned.
        stsReturn = self.m_objPCANBasic.GetErrorText(error,0x09)
        if stsReturn[0] != PCAN_ERROR_OK:
            return "An error occurred. Error-code's text ({0:X}h) couldn't be retrieved".format(error)
        else:
            message = str(stsReturn[1])
            return message.replace("'","",2).replace("b","",1)

    def GetDeviceName(self, handle):
        """
        Gets the name of a PCAN device

        Parameters:
            handle = PCAN-Basic Handle for getting the name

        Returns:
            The name of the handle
        """
        switcher = {
            PCAN_NONEBUS.value: "PCAN_NONEBUS",
            PCAN_PEAKCAN.value: "PCAN_PEAKCAN",
            PCAN_DNG.value: "PCAN_DNG",
            PCAN_PCI.value: "PCAN_PCI",
            PCAN_USB.value: "PCAN_USB",
            PCAN_VIRTUAL.value: "PCAN_VIRTUAL",
            PCAN_LAN.value: "PCAN_LAN"
        }

        return switcher.get(handle,"UNKNOWN")   

    def ConvertBitrateToString(self, bitrate):
        """
        Convert bitrate c_short value to readable string

        Parameters:
            bitrate = Bitrate to be converted

        Returns:
            A text with the converted bitrate
        """
        m_BAUDRATES = {PCAN_BAUD_1M.value:'1 MBit/sec', PCAN_BAUD_800K.value:'800 kBit/sec', PCAN_BAUD_500K.value:'500 kBit/sec', PCAN_BAUD_250K.value:'250 kBit/sec',
                       PCAN_BAUD_125K.value:'125 kBit/sec', PCAN_BAUD_100K.value:'100 kBit/sec', PCAN_BAUD_95K.value:'95,238 kBit/sec', PCAN_BAUD_83K.value:'83,333 kBit/sec',
                       PCAN_BAUD_50K.value:'50 kBit/sec', PCAN_BAUD_47K.value:'47,619 kBit/sec', PCAN_BAUD_33K.value:'33,333 kBit/sec', PCAN_BAUD_20K.value:'20 kBit/sec',
                       PCAN_BAUD_10K.value:'10 kBit/sec', PCAN_BAUD_5K.value:'5 kBit/sec'}
        return m_BAUDRATES[bitrate.value]

    def ConvertBytesToString(self, bytes):
        """
        Convert bytes value to string

        Parameters:
            bytes = Bytes to be converted

        Returns:
            Converted bytes value as string
        """
        return str(bytes).replace("'","",2).replace("b","",1)
    #endregion

## Starts the program
ManualWrite()