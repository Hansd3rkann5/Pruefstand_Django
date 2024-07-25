import time
import json
import sys, os
import serial
import pruefstand.pycrc as pycrc
import time
import yaml
import numpy as np
import itertools
from pruefstand import pycrc
from enum import Enum
from django.http import JsonResponse
from threading import Thread
from typing import Literal
from channels.generic.websocket import WebsocketConsumer
from .PCAN.libpcanbasic.examples.console.Python.ManualRead.ManualRead import ManualRead

    
def show_error(exception):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno, exception)

class ModBusRelay():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.serial = serial.Serial("/dev/ttyS0",9600,timeout=1)    
        self.cmd = [0x01, 0x05, 0, 0, 0, 0, 0, 0]
        self.comps = ["Motor", "Display", "Battery", "Charger", "Range EXT", "Service Dongle"]
        self.config = yaml.safe_load(open(f"komp_pruefstand/static/Komponenten.yaml", "r"))
        self.set:list[int | None] = [None] * 6
        self.on = 0xFF
        self.off = 0x00
        self.flip = 0x55
        self.progress = 0
        
    # All relays off: 01 05 00 FF 00 00 FD FA
    def reset_all(self):
        """
        Resets all the relays on the Modbus RTU Relay.
        """
        self.set = [None] * 6
        try:
            self.cmd[3] = 0xFF
            self.cmd[4] = self.off
            self.cmd[6] = 0xFD
            self.cmd[7] = 0xFA
            print(f"all off: {self.cmd}")
            self.serial.write(self.cmd)
            time.sleep(0.5)
        except Exception as e:
            show_error(e)
        
    #Abspeichern der vom Client ausgewählten Komponenten in Array zum Setzen der Relais bei Test start
    # def switch_relay(self, id:int):
    #     """
    #     Function for setting the given relay.
        
    #     Parameters:
    #         id = relay to set
    #     """
    #     try:
    #         if id == None:
    #             self.set[self.cons.index(type)] = None
    #         else:
    #             self.set[self.cons.index(type)] = self.comps[type][id]["relay"]-1
    #             return self.set[self.cons.index(type)]
    #         time.sleep(0.02)
    #     except Exception as e:
    #         show_error(e)
    
    #Funktion zum Schreiben der Nachrichten auf BUS
    def serial_write(self, id:int, state_request: Literal['on', 'off', 'flip']):
        """
        Function for writing on the CAN-Bus to the Modbus RTU Relay and setting the given relays.
        Parameters:
            id = number of the relay to set
            state = string with the desired state for the relay (on, off, flip)
        """
        if state_request == 'on':
            state = self.on
        if state_request == 'off':
            state = self.off
        if state_request == 'flip':
            state = self.flip
        try:
            self.cmd[2] = 0
            self.cmd[3] = int(format(id, '#04x'), 16)
            self.cmd[4] = state
            self.cmd[5] = 0
            self.crc = pycrc.ModbusCRC(self.cmd[0:6])
            self.cmd[6] = self.crc & 0xFF
            self.cmd[7] = self.crc >> 8
            print(self.cmd)
            self.serial.write(self.cmd)
        except Exception as e:
            show_error(e)
    
    #
    def set_comp(self):
        """
        Function for setting the desired Component
        """
        print(f"comps: {self.set}")
        for i in range(len(self.set)):
            check = self.set[i]
            if check != None:
                self.serial_write(check, state_request='on')
                time.sleep(0.02)
        self.start_test()
                
    def start_test(self):
        while self.progress < 101:
            time.sleep(0.1)
            self.progress += 1
            return self.progress

####################################################################################################################

# Klasse für Kommunikation zwischen Server und Client
class TestConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = False
        self.modbus = ModBusRelay()
        self.progress = 0
        self.combinations:list[int | None] = []
        self.konfig = ()
        self.home = False
        self.index = 1
        
    def connect(self):
        self.accept()
        self.reset_vars()
    
    def reset_vars(self):
        """
        Function for reseting all the run variables and the relays on the Modbus RTU Relay.
        """
        self.running = True
        self.home = False
        self.modbus.reset_all()
        self.send_master()
        self.test = ''
        self.combinations = []
        self.index = 1
        
    #Funktion zum Senden der Nachrichten an Client - verallgemeinert mit "Message" und "Value"
    def _send(self, message, value):
        self.send(text_data=json.dumps({message: value}))
    
    def disconnect(self, close_code):
        self.running = False

    #Alle Funktionen für die Kommunikation zwischen Client und Server
    def receive(self, text_data):
        """
        Function for recieving and sending information between the server and the client and proceeding that information to the
        corresponding functions.
        """
        try:
            text_data_json = json.loads(text_data)
            type = text_data_json["type"]
            if type == "home":
                print("Home")
                self._send("home", None)
                self.home = True
                self.reset_vars()
                self.modbus.reset_all()
            if type == "konfig":
                self.test = type
                self._send(type, None)
                print("Test über Konfig-File")
            if type == "manuell_comp":
                print("Manuelle Komp. Auswahl")
                self._send(type, None)
                self.test = type
            if type == "auto":
                print("Automatisierter Durchlauf")
                self.test = type
                self._send(type, None)
            if type == "manuell_konfig":
                print("Manueller Durchlauf der Konfiguration")
                self.test = type
                self._send(type, None)
            if type == "set_combinations":
                print("set konfig")
                combinations = text_data_json["comb"]
                self.set_Relay(combinations)
            if type == "set_comb_manu":
                print("set combination manu")
            if type == "Konfig-File":
                print("Konfig-File recieved")
                self.home = True
                konfig = text_data_json["text"]
                f = open("komp_pruefstand/static/Konfig.txt", "w")
                f.write(konfig)
                f.close()
                self.check_konfig_file()
            if type == "next":
                self._send("progress", 0)
                time.sleep(0.05)
                self.run_combinations()
            if type == "stop":
                print("stop")
                self.stop()
        except Exception as e:
            show_error(e)
    
    def send_master(self):
        """
        Sends the Master-Config-File to the Client for displaying the possible choices to the user.
        """
        try:
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
                data = yaml.safe_load(f)
            self._send("components_names", data)
        except Exception as e:
            show_error(e)
    
    def run_demo(self):
        for x in range(1, 101):
            time.sleep(0.02)
            self._send("progress", x)
    
    def send_progress(self):
        if self.test == "manuell_comp":
            print(self.combinations)
            self._send("combinations", [self.combinations])
            self.modbus.set_comp()
            self.run_demo()
            time.sleep(1)
            self._send("done", None)
            #self.modbus.reset_all()
        if self.test == "auto":
            self.run_demo()
        if self.test == "manuell_konfig":
            self.run_demo()
            self._send("next", None)
    
    def set_Relay(self, combinations):
        comb = []
        try:
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
                data = yaml.safe_load(f)
                # for combination in combinations:
                #     print(combination)
                for combination in combinations:
                    for index, name in enumerate(data):
                        #print(num, index, name)
                        if combination[name] != None:
                            comb.append(data[name][combination[name]]['relay'])
                        else:
                            comb.append(None)
                    self.combinations.append(comb)
                    comb = []
                    #comb = []
            self._send("combinations", self.combinations)
            self.test = "auto"
            self.run_combinations()
            print('Alle Kombinatoriken geschalten')
        except Exception as e:
            show_error(e)

    def check_konfig_file(self):
        """
        Function that strips the by the user uploaded Konfig-File in category- and component-names and passes that information to the 'parser-function' for further analysis.
        Sends the recieved combination-possibilities to the client and passes them to the 'run_combinations-function'.
        """
        self.combinations = []
        try:
            self._send('Upload erfolgreich', 0)
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as y:
                with open(f"komp_pruefstand/static/Konfig.txt", "r") as t:
                    konfig = yaml.safe_load(y)
                    lines = t.readlines()
                    breaks = []
                    #relays = {}
                    #combinations = []
                    konfig_count = 1
                    for index, line in enumerate(lines):
                        l = line.find('\n')
                        if l == 0:
                            breaks.append(index)
                            konfig_count += 1
                    if konfig_count == 1:
                        self.combinations = self.parser(lines, konfig)
                    else:
                        print(f'Anzahl Konfigs: {konfig_count}')
                        konfigs = {}
                        v = 0
                        for k in range(len(breaks)):
                            konfigs[f'Konfig{k+1}'] = lines[v:breaks[k]]
                            v = breaks[k]+1
                            if k+1 == len(breaks):
                                konfigs[f'Konfig{k+2}'] = lines[v:len(lines)]
                        for k in range(konfig_count):
                            combination = self.parser(konfigs[f'Konfig{k+1}'], konfig)
                            if len(combination) == 1:
                                self.combinations.append(combination[0])
                            else:
                                for c in range(len(combination)):
                                    self.combinations.append(combination[c])
                    print(f'\nAnzahl der Kombinationen: {len(self.combinations)}\nCombinations{self.combinations}')
                    self._send("combinations", self.combinations)
                    print(self.test)
                    if self.test == "auto":
                        self.run_combinations()
                        print('Alle Kombinatoriken geschalten')
                        self._send("done", None)
                    if self.test == "manuell_konfig":
                        self.run_combinations()
                        if self.index == len(self.combinations) + 1:
                            print('Alle Kombinatoriken geschalten')
                            self._send("done", None)
        except Exception as e:
            show_error(e)
            
    def parser(self, lines:list[str], konfig:dict):
        """
        Function for parsing the uploaded Config-File from the user. Checks for wrong written category- (Motor, Display, etc.)
        and component-names (e.g. HPR50).
        Takes the individual components from each category and safes them in a list, which compares the given name of the component
        with the names in the Master-Konfig-File and gives back the individual stored number of the relay.
        
        Returns list of all the possible interconnections from the given Konfig-File.
        
        Parameters:
            lines = list of strings with the individual lines of the Konfig-File.txt
            
            konfig = dictionary of the loaded Master-Konfig-File in .yaml
        """
        cons = list(konfig.keys())
        relays = {}
        for key in cons:
            relays[key] = None
        for line in lines:
            string = line.rstrip()
            relay = []
            comp = [x.strip() for x in string.split(':', line.find(':'))]
            komma = line.find(",")
            if comp[0] == 'Range Ext' or comp[0] == 'RangeExt':
                comp[0] = 'Range EXT'
            if komma != -1:
                variants = [''] * len(konfig[comp[0]])
                choices = [x.strip() for x in comp[1].split(',')]
                if comp[0] == 'Battery' or comp[0] == 'Range EXT':
                    choices = self.check_kWh(choices)
                comp = comp[0]
                for i in range(len(konfig[comp])):
                    variants[i] = konfig[comp][i]['name']   #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
                print(f'Anzahl Wahl {comp}: {len(choices)}')
                odds = []
                for name in range(len(choices)):
                    if choices[name].strip() not in variants:
                        odds.append((choices[name].strip()))
                if len(odds) <= 1:
                    num = 'sind'
                    num1 = 'ist'
                else:
                    num = 'ist'
                    num1 = 'sind'
                if len(odds) != 0:
                    print(f'Davon {num} aber nur {len(choices) - len(odds)} gültig.')
                    print(f'{comp} {odds} {num1} ungültig')
                    odds.append(comp)
                    self._send("odds", odds)
                for i in range(len(choices)):
                    for index in range(len(konfig[comp])):
                        k = konfig[comp][index]['name']
                        if k == choices[i].strip():
                            relay.append((konfig[comp][index]["relay"]))
                            print(f'{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
                relay.sort()
                relays[comp] = relay
            elif comp[1] != 'None':
                if comp[0] == 'Battery' or comp[0] == 'Range EXT':
                    comp[1] = self.check_kWh(comp[1])
                for name in konfig[comp[0]]:
                    if name['name'] == comp[1]:
                        r = name['relay']
                relays[comp[0]] = [r]
                print(f'{comp[0]}, {comp[1]} hat Relay: {r}')
        print(f'Relays zu schalten: {relays}\n')
        l = []
        for key in relays:
            if relays[key] != None:
                l.append(relays[key])
            else:
                l.append([None])
        combinations = list(itertools.product(*l))
        return combinations
    
    def run_combinations(self):
        """
        Function that runs through the user selected configurations - according to the choice of 'auto' or 'manual' - and sets the relays of an
        individual combination in the list of all possible combinations. It also sends the current number of the running combination to the client
        for displaying it to the user.
        """
        if self.test == "auto":
            for index, combination in enumerate(self.combinations, start=1):
                print(f'Combination: {index}')
                print(self.combinations)
                #time.sleep(1)
                self._send("testnum", index)
                for rel in range(len(combination)):
                    if combination[rel] != None:
                        self.modbus.serial_write(id=combination[rel]-1, state_request='on')
                        time.sleep(0.02)
                self.send_progress()
                time.sleep(0.5)
                self.modbus.reset_all()
                self._send("progress", 0)
        if self.test == "manuell_konfig":
            if self.index != len(self.combinations) + 1:
                print("break")
                combination = self.combinations[self.index - 1]
                print(self.combinations)
                print(f'Combination: {self.index}')
                self._send("testnum", self.index)
                for rel in range(len(combination)):
                    if combination[rel] != None:
                        self.modbus.serial_write(combination[rel]-1, 'on')
                        time.sleep(0.02)
                self.send_progress()
                time.sleep(0.5)
                self.index += 1
                self.modbus.reset_all()
            if self.index == len(self.combinations) +1:
                print('Alle Kombinatoriken geschalten')
                self._send("done", None)
        else:
            self._send("done", None)
    
    def check_kWh(self, choices:str):
        """
        Function for checking the Konfig-File on wrong written 'kWh' unit for comparison with Master-Konfig-File.
        
        Returns string with corrected written unit
        
        Parameters:
            choices = string of current component choices (Motor, Display, ect.)
        """
        if type(choices) != str:
            for ind, choice in enumerate(choices):
                t = choice[-4:]
                if choice[-4:] != ' kWh':
                    k = choice.find('k')
                    #print(f'Index of k: {battery.find("k")}')
                    choice = choice[:k] + ' ' + choice[k:]
                    choices[ind] = choice
        else:
            x = choices[-4:]
            if choices[-4:] != ' kWh':
                k = choices.find('k')
                #print(f'Index of k: {choices.find("k")}')
                choices = choices[:k] + ' ' + choices[k:]
        return choices

    def stop(self):
        self.running = False
        
#Thomas Zengerle
#Matthias Schoppe