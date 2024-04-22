import time
import json
import sys, os
import serial
import pruefstand.pycrc as pycrc
import time
import yaml
import itertools
from django.http import JsonResponse
from threading import Thread
from channels.generic.websocket import WebsocketConsumer

def show_error(exception):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno, exception)

class ModBusRelay():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.serial = serial.Serial("/dev/ttyS0",9600,timeout=1)    
        self.cmd = [0x01, 0x05, 0, 0, 0, 0, 0, 0]
        self.cons = ["Motor", "Display", "Battery", "Charger", "Range EXT", "Service Dongle"]
        self.comps = yaml.safe_load(open(f"komp_pruefstand/static/Komponenten/Komponenten.yaml", "r"))
        self.set = [None] * 6
        self.status = 0x00
        self.on = 0xFF
        self.off = 0x00
        self.flip = 0x55
        self.progress = 0
        
    # All relays off: 01 05 00 FF 00 00 FD FA
    def reset_all(self):
        self.status = self.off
        self.set = [None] * 6
        try:
            self.cmd[3] = 0xFF
            self.cmd[4] = self.status
            self.cmd[6] = 0xFD
            self.cmd[7] = 0xFA
            print(f"all off: {self.cmd}")
            #self.serial.write(self.cmd)
        except Exception as e:
            show_error(e)
        
    #Abspeichern der vom Client ausgewählten Komponenten in Array zum Setzen der Relais bei Test start
    def switch_relay(self, type, id):
        try:
            if type in self.cons:
                if id == None:
                    self.set[self.cons.index(type)] = None
                else:
                    self.set[self.cons.index(type)] = self.comps[type][id]["relay"]-1
            time.sleep(0.02)
        except Exception as e:
            show_error(e)
    
    #Funktion zum Schreiben der Nachrichten auf BUS
    def serial_write(self, id):
        try:
            self.cmd[2] = 0
            self.cmd[3] = int(format(id, '#04x'), 16)
            self.cmd[4] = self.status  #Relay Flip
            self.cmd[5] = 0
            self.crc = pycrc.ModbusCRC(self.cmd[0:6])
            self.cmd[6] = self.crc & 0xFF
            self.cmd[7] = self.crc >> 8
            print(self.cmd)
            #self.serial.write(self.cmd)
        except Exception as e:
            show_error(e)
    
    #
    def set_comp(self):
        print(f"comps: {self.set}")
        self.status = self.on
        for i in range(len(self.set)):
            if self.set[i] != None:
                self.serial_write(self.set[i])
                time.sleep(0.02)
        self.start_test()
                
    def start_test(self):
        while self.progress < 101:
            time.sleep(0.1)
            self.progress += 1
            return self.progress


# Klasse für Kommunikation zwischen Server und Client
class TestConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        self.modbus = ModBusRelay()
        self.progress = 0
        self.test = ''
        self.combinations = []
        
    def connect(self):
        self.accept()
        self.running = True
        self.modbus.reset_all()
        self.send_num()
        self.test = ''
    
    #Funktion zum Senden der Nachrichten an Client - verallgemeinert mit "Message" und "Value"
    def _send(self, message, value):
        self.send(text_data=json.dumps({message: value}))
    
    def disconnect(self, close_code):
        self.running = False

    #Alle Funktionen für die Kommunikation zwischen Client und Server
    def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            type = text_data_json["type"]
            if type == "home":
                print("Home")
                self.modbus.reset_all()
            if type == "konfig":
                print("Test über Konfig-File")
            if type == "manu":
                print("Manuelle Komp. Auswahl")
                self.send_num()
                type = text_data_json["type"]
            if type == "auto":
                print("Automatisierter Durchlauf")
                self.test = type
                type = text_data_json["type"]
            if type == "manuell":
                print("Manueller Durchlauf")
                self.test = type
                type = text_data_json["type"]
            if type in self.modbus.cons:
                id = text_data_json["id"]
                self.set_Relay(type, id)
                #self.modbus.comps[type][id]["relay"]
            if type == "set_konfig":
                print("set konfig")
                self.send_progress()
            if type == "Konfig-File":
                print("Konfig-File recieved")
                konfig = text_data_json["text"]
                #try:
                f = open("komp_pruefstand/static/Komponenten/Konfig.txt", "w")
                f.write(konfig)
                f.close()
                self.check_konfig_file()
                #except Exception as e:
                #    show_error(e)
                #print(konfig)
            if type == "stop":
                print("stop")
                self.stop()
        except Exception as e:
            show_error(e)
    
    def send_num(self):
        try:
            with open(f"komp_pruefstand/static/Komponenten/Komponenten.yaml", "r") as f:
                data = yaml.safe_load(f)
            self._send("components_names", data)
        except Exception as e:
            show_error(e)
    
    def send_progress(self):
        self.modbus.set_comp()
        for x in range(1, 101):
            time.sleep(0.05)
            self._send("progress", x)
        time.sleep(1)
        self._send("done", None)
    
    def set_Relay(self, type, id):
        print(f"Type: {type}, id: {id}")
        try:
            self.modbus.switch_relay(type, id)
        except Exception as e:
            show_error(e)

    def check_konfig_file(self):
        try:
            self._send('Upload erfolgreich', 0)
            with open(f"komp_pruefstand/static/Komponenten/Komponenten.yaml", "r") as y:
                with open(f"komp_pruefstand/static/Komponenten/Konfig.txt", "r") as t:
                    konfig = yaml.safe_load(y)
                    cons = list(konfig.keys())
                    p = t.readlines()
                    relays = {}
                    for key in cons:
                        relays[key] = None
                    for line in p:
                        string = line.rstrip()
                        relay = []
                        comp = [x.strip() for x in string.split(':', line.find(':'))]
                        komma = line.find(",")
                        if comp[0] == 'Range Ext' or comp[0] == 'RangeExt':
                            comp[0] = 'Range EXT'
                        if komma != -1:
                            variants = [''] * len(konfig[comp[0]])
                            choices = [x.strip() for x in comp[1].split(','0)]
                            comp = comp[0]
                            for i in range(len(konfig[comp])):
                                variants[i] = konfig[comp][i]['name']   #Array mit Namen der Unterkomponenten, von Komp, wo Aushwahl > 1
                            print(f'\nAnzahl Wahl {comp}: {len(choices)}')
                            odds = []
                            for name in range(len(choices)):
                                if choices[name].strip() not in variants:
                                    odds.append((choices[name].strip()))
                            if len(odds) > 1:
                                num = 'sind'
                            else:
                                num = 'ist'
                            if len(odds) != 0:
                                print(f'Davon {num} aber nur {len(choices) - len(odds)} gültig.')
                                print(f'{comp} {odds} {num} ungültig')
                            for i in range(len(choices)):
                                for index in range(len(konfig[comp])):
                                    k = konfig[comp][index]['name']
                                    if k == choices[i].strip():
                                        relay.append((konfig[comp][index]["relay"]))
                                        print(f'{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
                            relay.sort()
                            relays[comp] = relay
                        elif comp[1] != 'None':
                            relays[comp[0]] = [(konfig[comp[0]][0]["relay"])]
                            print(f'{comp[0]}, {comp[1]} hat Relay: {konfig[comp[0]][0]["relay"]}')
                    print(f'Relays zu schalten: {relays}')
            l = []
            if self.test == "auto":
                for key in relays:
                    if relays[key] != None:
                        l.append(relays[key])
                    else:
                        l.append([-1])
                self.combinations = list(itertools.product(*l))
                i = 1
                print(f'\nAnzahl der Kombinationen: {len(self.combinations)}')
                for combination in self.combinations:
                    print(f'Combination: {i}')
                    i += 1
                    for rel in range(len(combination)):
                        self.modbus.serial_write(rel)
                        time.sleep(0.2)
                    time.sleep(1)
                print('Alle Kombinatoriken geschalten')
        except Exception as e:
            show_error(e)
                
    def stop(self):
        self.running = False