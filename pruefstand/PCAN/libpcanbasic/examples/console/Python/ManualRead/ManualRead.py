## Needed Imports
try:
    from .PCANBasic import *
except ImportError:
    from PCANBasic import *
import os
import sys
import time
import logging
import crcmod.predefined
from binascii import unhexlify
from threading import Thread
import crc16
import json





#PD: Prozess Daten
#SD: Service Daten
PRIO1_SOURCENODE = 1
PRIO2_RFU        = 2
PRIO3_TARGETNODE = 3

logger = logging.getLogger('my-logger')


#Knotenadressen
NODE_ADRESSES = {
    'MOTORSTEUERUNG'      : 0x01,
    'SCHIEBEHILFEGERAET'  : 0x0F,
    'BMS'                 : 0x10,
    'LADEPORT'            : 0x12,
    'DISPLAY'             : 0x15,
    'LICHT'               : 0x20,
    'ECONNECT'            : 0x25,
    'GPSTUNER'            : 0x2A,
    'SMARTBOX'            : 0x2E,
    'SERVICEMODUL'        : 0x3D,
    'ENTWICKLUNGSTOOLS'   : 0x3E
}

#Prio1 Message-IDs
P1_MESSAGE_IDS = {
    'P1_MSG_EMCYOFF'          : 0x0,
    'P1_MSG_EMCY'           : 0x1,
    'P1_MSG_SYNC'            : 0x2,
    'P1_MSG_PRIO_BROADCAST'   : 0x3,
    'P1_MSG_REPLPD'           : 0x7,
    'P1_MSG_REPLSD'           : 0x8,
    'P1_MSG_ACKNPD'           : 0x9,
    'P1_MSG_ACKNSD'           : 0xA,
    'P1_MSG_INFO'             : 0xC,
    'P1_MSG_WARNING'          : 0xD,
    'P1_MSG_BROADCAST'        : 0xE,
    'P1_MSG_SLAVECHG'         : 0xF
    }

#Prio3 Message-IDs
P3_MESSAGE_IDS = {
    'P3_MSG_PDR'   : 0x00,
    'P3_MSG_PDW'   : 0x01,
    'P3_MSG_SDR'   : 0x02,
    'P3_MSG_SDW'   : 0x03
}

class Message():
    def __init__(self, msg):
        self.can_id_hex = GetIdString(msg.ID, msg.MSGTYPE)
        self.bits = bin(int(self.can_id_hex, 16))[2:].zfill(11)
        self.length:int=msg.LEN
        self.node = 0x0
        self.id = 'No Match'
        self.prio = 'No Match'
        self.data = GetDataString(msg.DATA,msg.MSGTYPE)
        self.id_bits = 'No Match'
        self.id_hex = 'No Match'
        self.node_adress_bits = 'No Match'
        self.node_adress_hex = 'No Match'

        if str(self.bits[:1]) == '0':
            self.prio = 'Prio1'
            self.id_bits = self.bits[1:5]
            self.id_hex = hex(int(self.id_bits, 2))
            self.node_adress_bits = self.bits[5:]
            self.node_adress_hex = hex(int(self.node_adress_bits, 2))
            self.id = self.get_id(P1_MESSAGE_IDS, self.id_hex)
            self.node = self.get_node(self.node_adress_hex)
        # if str(self.bits[:2]) == '10':
        #     self.Prio = 'Prio2'
        if str(self.bits[:2]) == '11':
            self.prio = 'Prio3'
            self.id_bits = self.bits[8:]
            self.id_hex = hex(int(self.id_bits, 2))
            self.node_adress_bits = self.bits[2:8]
            self.node_adress_hex = hex(int(self.node_adress_bits, 2))
            self.id = self.get_id(P3_MESSAGE_IDS, self.id_hex)
            self.node = self.get_node(self.node_adress_hex)
        
    def __str__(self):
        strung=""
        strung+='Node: ' + str(self.node) + '\n'
        strung+='CAN-ID: ' + self.can_id_hex
        strung+='\nMSG-ID: ' + str(self.id)
        strung+="\nData: " + self.data
        strung+="\nLength: " + str(self.length)
        strung+="\n-------------------------------------------"
        return strung
    
    def get_id(self, database, id_hex):
        for id in database:
            if hex(database[id]) == id_hex:
                return id
        return 'no match'
            
    def get_node(self, node_adress_hex):
        for key in NODE_ADRESSES:
            if hex(NODE_ADRESSES[key]) == node_adress_hex:
                return key
        return 'no match'


def count():
    i = 1
    while i < 11:
        print(f'{i} sec')
        time.sleep(1)
        i+=1
    print("done")
class ManualRead():

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

    def __init__(self, interactive=False):
        """
        Create an object starts the programm
        """
        self.inter = interactive
        self.msgCanMessage = TPCANMsg()
        self.msgCanMessage.LEN = 8
        self.msgCanMessage.MSGTYPE = PCAN_MESSAGE_EXTENDED.value
        self.ShowConfigurationHelp() ## Shows information about this sample
        self.ShowCurrentConfiguration() ## Shows the current parameters configuration
        self.c = 0
        self.k = []
        self.ids = []
        self.messages:list[Message] = []
        self.nodes_p1 = {}
        self.nodes_p3 = {}
        for node in NODE_ADRESSES:
            self.nodes_p1[node] = {}
            self.nodes_p3[node] = {}
            for key in P1_MESSAGE_IDS:
                self.nodes_p1[node][key] = 0
            for key in P3_MESSAGE_IDS:
                self.nodes_p3[node][key] = 0
        self.all = {'Prio1': self.nodes_p1, 'Prio3': self.nodes_p3, 'No Match': 0}
                

        ## Checks if PCANBasic.dll is available, if not, the program terminates
        try:
            self.m_objPCANBasic = PCANBasic()
            self.m_DLLFound = True
        except :
            logger.debug("Unable to find the library: PCANBasic.dll !")
            if interactive:
                self.getInput("Press <Enter> to quit...")
            self.m_DLLFound = False
            return

        ## Initialization of the selected channel
        if self.IsFD:
            stsResult = self.m_objPCANBasic.InitializeFD(self.PcanHandle,self.BitrateFD)
        else:
            stsResult = self.m_objPCANBasic.Initialize(self.PcanHandle,self.Bitrate)

        if stsResult != PCAN_ERROR_OK:
            logger.debug("Can not initialize. Please check the defines in the code.")
            self.ShowStatus(stsResult)
            logger.debug("")
            if interactive:
                self.getInput("Press <Enter> to quit...")
            return
        ## Reading messages...
        logger.debug("Successfully initialized.")
        if interactive:
            self.getInput("Press <Enter> to read...")
            self.read()
    
    def write(self):
        p = 1
        by = []
        #self.clear()
        #while strinput == "y":
        for i in range(0, 1, 1):
            for j in range(20):
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
                time.sleep(0.5)
                by = []
                self.crc = list('0300000000')                    
            #self.crc[:2] = 
            #strinput = self.getInput("Do you want to write again? yes[y] or any other key to exit...", "y")
            #strinput = chr(ord(strinput))        
            
    def read(self):
        strinput = "y"
        i = 0
        x = Thread(target = count, name="runlocalscript")
        write = Thread(target = self.write, name="runlocalscript")
        x.start()
        t0 = time.time()
        while strinput == "y" and (time.time() - t0) < 11:
            self.clear()
            self.ReadMessages(i)
            #write.start()
        sum = 0
        for message in self.messages:
            if message.prio != 'No Match':
                for node in NODE_ADRESSES:
                    for msg_id in P1_MESSAGE_IDS:
                        if message.node == node:
                            if message.id == msg_id:
                                self.all[message.prio][message.node][message.id] += 1
                    for msg_id in P3_MESSAGE_IDS:
                        if message.node == node:
                            if message.id == msg_id:
                                self.all[message.prio][message.node][message.id] += 1
            else:
                self.all[message.prio] += 1
        for prio in self.all:
            if prio != 'No Match':
                logger.debug(f'\n{prio}\n----------------------')
                for node in self.all[prio]:
                    logger.debug(node)
                    for id in self.all[prio][node]:
                        sum += self.all[prio][node][id]
                        logger.debug(f'{id}: {self.all[prio][node][id]}')
                    self.all[prio][node]['Summe'] = sum
                    logger.debug(f"Gesamt: {self.all[prio][node]['Summe']}")
                    logger.debug("-------------------------")
                    sum = 0
            else:
                logger.debug(f'\n{prio}: {self.all[prio]}')
        if self.inter:
            with open('komp_pruefstand/static/can.txt','w') as file:
                file.write(json.dumps(self.all, indent=4))
        logger.debug("-------------------------")
        for message in self.messages:
            if message.prio == 'Prio1' and message.node == 'DISPLAY' and message.id == 'P1_MSG_EMCY':
                    logger.debug(message)
            if message.can_id_hex == '68ö':
                logger.debug(message)
        return self.all
        
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
    def ReadMessages(self, i):
        """
        Function for reading PCAN-Basic messages
        """
        stsResult = PCAN_ERROR_OK

        ## We read at least one time the queue looking for messages. If a message is found, we look again trying to 
        ## find more. If the queue is empty or an error occurr, we get out from the dowhile statement.
        while (not (stsResult & PCAN_ERROR_QRCVEMPTY)):
            if self.IsFD:
                stsResult = self.ReadMessageFD()
            else:
                stsResult = self.ReadMessage(i)
            if stsResult != PCAN_ERROR_OK and stsResult != PCAN_ERROR_QRCVEMPTY:
                self.ShowStatus(stsResult)
                return

    def ReadMessage(self, i):
        """
        Function for reading CAN messages on normal CAN devices

        Returns:
            A TPCANStatus error code
        """
        ## We execute the "Read" function of the PCANBasic   
        stsResult = self.m_objPCANBasic.Read(self.PcanHandle)

        if stsResult[0] == PCAN_ERROR_OK:
            self.ProcessMessageCan(stsResult[1],stsResult[2], i)
            
        return stsResult[0]

    def ReadMessageFD(self):
        """
        Function for reading messages on FD devices

        Returns:
            A TPCANStatus error code
        """
        ## We execute the "Read" function of the PCANBasic    
        stsResult = self.m_objPCANBasic.ReadFD(self.PcanHandle)

        if stsResult[0] == PCAN_ERROR_OK:
            ## We show the received message
            self.ProcessMessageCanFd(stsResult[1],stsResult[2])
            
        return stsResult[0]

    def ProcessMessageCan(self,msg,itstimestamp, i):
        #jere
        """
        Processes a received CAN message

        Parameters:
            msg = The received PCAN-Basic CAN message
            itstimestamp = Timestamp of the message as TPCANTimestamp structure
        """
        microsTimeStamp = itstimestamp.micros + 1000 * itstimestamp.millis + 0x100000000 * 1000 * itstimestamp.millis_overflow
        formatted_msg=Message(msg)
        if formatted_msg.bits not in self.ids:
            self.ids.append(formatted_msg.bits)
        #if formatted_msg.node == 'SCHIEBEHILFEGERAET':
        #print(formatted_msg.can_id_hex)
        #print(formatted_msg.data)
            #later = time.time()
            #print(later-now)
        self.messages.append(formatted_msg)
        # logger.debug(f"Node:  {formatted_msg.node}")
        # logger.debug(f"CAN-ID Bits:  {formatted_msg.bits}")
        # logger.debug(f"CAN-ID Hex: {formatted_msg.can_id_hex}")
        # logger.debug(f"Msg-ID Bits: {formatted_msg.id_bits}")
        # logger.debug(f"Msg-ID Hex:  {formatted_msg.id_hex}")
        # logger.debug(f"Node Bits:  {formatted_msg.node_adress_bits}")
        # logger.debug(f"Nodes Hex:  {formatted_msg.node_adress_hex}")
        # logger.debug(f"Data: {formatted_msg.data}")
        # logger.debug("-----------------------------")

    def ProcessMessageCanFd(self, msg, itstimestamp):
        """
        Processes a received CAN-FD message

        Parameters:
            msg = The received PCAN-Basic CAN-FD message
            itstimestamp = Timestamp of the message as microseconds (ulong)
        """
        logger.debug("Type: " + GetTypeString(msg.MSGTYPE))
        logger.debug("ID: " + GetIdString(msg.ID, msg.MSGTYPE))
        logger.debug("Length: " + str(GetLengthFromDLC(msg.DLC)))
        logger.debug("Time: " + GetTimeString(itstimestamp))
        logger.debug("Data: " + GetDataString(msg.DATA,msg.MSGTYPE))
        logger.debug("----------------------hhvhvh------------------------------------")
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
            pass
            #os.system('clear')
        
    def ShowConfigurationHelp(self):
        """
        Shows/prints the configurable parameters for this sample and information about them
        """
        logger.debug("=========================================================================================")
        logger.debug("|                        PCAN-Basic ManualRead Example                                   |")
        logger.debug("=========================================================================================")
        logger.debug("Following parameters are to be adjusted before launching, according to the hardware used |")
        logger.debug("                                                                                         |")
        logger.debug("* PcanHandle: Numeric value that represents the handle of the PCAN-Basic channel to use. |")
        logger.debug("              See 'PCAN-Handle Definitions' within the documentation                     |")
        logger.debug("* IsFD: Boolean value that indicates the communication mode, CAN (false) or CAN-FD (true)|")
        logger.debug("* Bitrate: Numeric value that represents the BTR0/BR1 bitrate value to be used for CAN   |")
        logger.debug("           communication                                                                 |")
        logger.debug("* BitrateFD: String value that represents the nominal/data bitrate value to be used for  |")
        logger.debug("             CAN-FD communication                                                        |")
        logger.debug("=========================================================================================")
        logger.debug("")

    def ShowCurrentConfiguration(self):
        """
        Shows/prints the configured paramters
        """
        logger.debug("Parameter values used")
        logger.debug("----------------------")
        logger.debug("* PCANHandle: " + self.FormatChannelName(self.PcanHandle))
        logger.debug("* IsFD: " + str(self.IsFD))
        logger.debug("* Bitrate: " + ConvertBitrateToString(self.Bitrate))
        logger.debug("* BitrateFD: " + ConvertBytesToString(self.BitrateFD))
        logger.debug("")

    def ShowStatus(self,status):
        """
        Shows formatted status

        Parameters:
            status = Will be formatted
        """
        logger.debug("=========================================================================================")
        logger.debug(self.GetFormattedError(status))
        logger.debug("=========================================================================================")
    
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
           return ('%s:FD %s (%.2X)' % (GetDeviceName(devDevice.value), byChannel, handleValue))
        else:
           return ('%s %s (%.2X)' % (GetDeviceName(devDevice.value), byChannel, handleValue))

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

def GetLengthFromDLC(dlc):
    """
    Gets the data length of a CAN message

    Parameters:
        dlc = Data length code of a CAN message

    Returns:
        Data length as integer represented by the given DLC code
    """
    if dlc == 9:
        return 12
    elif dlc == 10:
        return 16
    elif dlc == 11:
        return 20
    elif dlc == 12:
        return 24
    elif dlc == 13:
        return 32
    elif dlc == 14:
        return 48
    elif dlc == 15:
        return 64
    
    return dlc

def GetIdString(id, msgtype):
    """
    Gets the string representation of the ID of a CAN message

    Parameters:
        id = Id to be parsed
        msgtype = Type flags of the message the Id belong

    Returns:
        Hexadecimal representation of the ID of a CAN message
    """
    if (msgtype & PCAN_MESSAGE_EXTENDED.value) == PCAN_MESSAGE_EXTENDED.value:
        return '%.8X' %id
    else:
        return '%.3X' %id

def GetTimeString(time):
    """
    Gets the string representation of the timestamp of a CAN message, in milliseconds

    Parameters:
        time = Timestamp in microseconds

    Returns:
        String representing the timestamp in milliseconds
    """
    fTime = time / 1000.0
    return '%.1f' %fTime

def GetTypeString(msgtype):  
    """
    Gets the string representation of the type of a CAN message

    Parameters:
        msgtype = Type of a CAN message

    Returns:
        The type of the CAN message as string
    """
    if (msgtype & PCAN_MESSAGE_STATUS.value) == PCAN_MESSAGE_STATUS.value:
        return 'STATUS'
    
    if (msgtype & PCAN_MESSAGE_ERRFRAME.value) == PCAN_MESSAGE_ERRFRAME.value:
        return 'ERROR'        
    
    if (msgtype & PCAN_MESSAGE_EXTENDED.value) == PCAN_MESSAGE_EXTENDED.value:
        strTemp = 'EXT'
    else:
        strTemp = 'STD'

    if (msgtype & PCAN_MESSAGE_RTR.value) == PCAN_MESSAGE_RTR.value:
        strTemp += '/RTR'
    else:
        if (msgtype > PCAN_MESSAGE_EXTENDED.value):
            strTemp += ' ['
            if (msgtype & PCAN_MESSAGE_FD.value) == PCAN_MESSAGE_FD.value:
                strTemp += ' FD'
            if (msgtype & PCAN_MESSAGE_BRS.value) == PCAN_MESSAGE_BRS.value:                    
                strTemp += ' BRS'
            if (msgtype & PCAN_MESSAGE_ESI.value) == PCAN_MESSAGE_ESI.value:
                strTemp += ' ESI'
            strTemp += ' ]'
            
    return strTemp

def GetDataString(data, msgtype):
    """
    Gets the data of a CAN message as a string

    Parameters:
        data = Array of bytes containing the data to parse
        msgtype = Type flags of the message the data belong

    Returns:
        A string with hexadecimal formatted data bytes of a CAN message
    """
    if (msgtype & PCAN_MESSAGE_RTR.value) == PCAN_MESSAGE_RTR.value:
        return "Remote Request"
    else:
        strTemp = b""
        for x in data:
            strTemp += b'%.2X ' % x
        return str(strTemp).replace("'","",2).replace("b","",1)

def GetDeviceName(handle):
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

def ConvertBitrateToString(bitrate):
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

def ConvertBytesToString(bytes):
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
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    ManualRead(True)

#schicken konfigurierte KOmponenten Nachrichtun und sind da/ansprechbar? PRIO
#keine Komp darf fehlermeldung rausschicken PRIO
#(funktioniert WALK modus als geringste funktionsabfrage einer Konfig)