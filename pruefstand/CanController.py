import can
import time

PRIO1_SOURCENODE = 1
PRIO2_RFU        = 2
PRIO3_TARGETNODE = 3

P1_MSG_EMCYOFF  = 0x00
P1_MSG_EMCY     = 0x01
P1_MSG_SYNC     = 0x02
P1_MSG_PRIO_BROADCAST = 0x03
P1_MSG_REPLPD   = 0x07
P1_MSG_REPLSD   = 0x08
P1_MSG_ACKNPD   = 0x09
P1_MSG_ACKNSD   = 0x0A
P1_MSG_INFO     = 0x0C
P1_MSG_WARNING  = 0x0D
P1_MSG_BROADCAST= 0x0E
P1_MSG_SLAVECHG = 0x0F

P3_MSG_PDR   = 0x00
P3_MSG_PDW   = 0x01
P3_MSG_SDR   = 0x02
P3_MSG_SDW   = 0x03

class CanController:
    def __init__(self):
        self.bus = None

    def Connect_CAN(self):
        print("Connecting CAN")
        self.bus = can.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=500000)

    def Disconnect_CAN(self):
        self.bus.shutdown()

    def Send_Message(self, id, array):
        
        msg = can.Message(
            arbitration_id=id, 
            data=array, 
            is_extended_id=False
        )

        try:
            self.bus.send(msg)
            print("Message sent on " + self.bus.channel_info)
            print(msg)
        except can.CanError:
            print("Message NOT sent")


    def Wait_Message(self, id, data, timeout):
        
        start = time.time()

        print("Receiving messages on " + self.bus.channel_info)
        while (time.time() < start + timeout):
            msg = self.bus.recv(timeout)
            print(msg)

            if msg == None:
                return None

            if (msg.arbitration_id == id) and data == list(msg.data[:len(data)]):
                return msg
            
        print("Message timeout after " + str(timeout) + "s")

        return None
    

    def Read_Param(self, node, param):
        if (isinstance(node,str)):  
            if ("x" in node):
                node = int(node,16)
            else:
                node = int(node)

        if (isinstance(param,str)):  
            if ("x" in param):
                param = int(param,16)
            else:
                param = int(param)

        canID = PRIO3_TARGETNODE << 9 | node << 3 | P3_MSG_SDR
        canID_reply = P1_MSG_REPLSD << 6 | node

        array = [param & 0xFF, (param >> 8) & 0xFF]

        self.Send_Message(canID, array)

        msg = self.Wait_Message(canID_reply, [0x01] + array, 0.1)

        if msg == None:
            raise Exception("Expected CAN Message timeout")

        valueArr = msg.data[3:]
        value = int.from_bytes(valueArr, 'little')

        print("Received value " + str(value))
        return value
    

    def Write_Param(self, node, param, value, ack = True):
        if (isinstance(node,str)):
            if ("x" in node):
                node = int(node,16)
            else:
                node = int(node)

        if (isinstance(param,str)):  
            if ("x" in param):
                param = int(param,16)
            else:
                param = int(param)

        if (isinstance(value,str)):     
            if ("x" in value):
                value = int(value,16)
            else:
                value = int(value)

        canID = PRIO3_TARGETNODE << 9 | node << 3 | P3_MSG_SDW
        canID_reply = P1_MSG_ACKNPD << 6 | node

        array = list(param.to_bytes(2, 'little')) + list(value.to_bytes(4, 'little'))

        self.Send_Message(canID, array)

        if (ack == False):
            return None

        msg = self.Wait_Message(canID_reply, [0x01] + array, 0.1)

        if msg == None:
            return None

        valueArr = msg.data[3:]
        value = int.from_bytes(valueArr, 'little')

        print("Received value " + str(value))
        return value

    def Reset_Node(self, node):
        if (isinstance(node,str)):
            if ("x" in node):
                node = int(node,16)
            else:
                node = int(node)

        self.Write_Param(node, 0x1010, 0xAA55)
        self.Write_Param(node, 0x1010, 0x55AA, False)

        canID_reply = P1_MSG_SLAVECHG << 6 | node

        start = time.time()

        while time.time() < start + 3.0:
            msg = self.Wait_Message(canID_reply, [], 3.0)

            if msg == None:
                return
            
            if msg.data[1] == 2:
                print("Application SlaveChange received")
                return
        
        print("Reset Timeout")
        
        