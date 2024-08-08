import time
import json
import sys, os
import serial
import pruefstand.pycrc as pycrc
import time
import yaml
import numpy as np
import itertools
import re
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
        self.serial = serial.Serial("/dev/ttyS0",9600,timeout=1)    #Definierung des Ausgangs und der Baudrate fuer Bus
        self.cmd = [0x01, 0x05, 0, 0, 0, 0, 0, 0]   #Array fuer RS485-Nachricht
        self.comps = ["Motor", "Display", "Battery", "Charger", "Range EXT", "Service Dongle"]  #Array mit Strings der Komponenten
        self.config = yaml.safe_load(open(f"komp_pruefstand/static/Komponenten.yaml", "r"))
        self.set:list[int | None] = [None] * 6  #Leerer Array zum abspeichern der zu schaltenden Relais
        self.ON = 0xFF          #Byte zum Einschalten der Relais
        self.OFF = 0x00         #Byte zum Ausschalten der Relais
        self.FLIP = 0x55         #Byte fuer einen Flip des Relais (on <-> off)
        self.progress = 0
        
    # All relays off: 01 05 00 FF 00 00 FD FA
    def reset_all(self):
        """
        Resets all the relays on the Modbus RTU Relay.
        """
        self.set = [None] * 6
        try:
            self.cmd[3] = 0xFF
            self.cmd[4] = self.OFF
            self.cmd[6] = 0xFD
            self.cmd[7] = 0xFA
            print(f"all off: {self.cmd}")
            self.serial.write(self.cmd)
            time.sleep(0.5)
        except Exception as e:
            show_error(e)
    
    #Funktion zum Schreiben der Nachrichten auf BUS
    def serial_write(self, id:int, state_request: Literal['on', 'off', 'flip']):
        """
        Function for writing on the CAN-Bus to the Modbus RTU Relay and setting the given relays.
        Parameters:
            id = number of the relay to set
            state = string with the desired state for the relay (on, off, flip)
        """
        try:
            self.cmd[2] = 0
            self.cmd[3] = int(format(id, '#04x'), 16)
            if state_request == 'on':
                self.cmd[4] = self.ON
            if state_request == 'off':
                self.cmd[4] = self.OFF
            if state_request == 'flip':
                self.cmd[4] = self.FLIP
            self.cmd[5] = 0
            self.crc = pycrc.ModbusCRC(self.cmd[0:6])
            self.cmd[6] = self.crc & 0xFF
            self.cmd[7] = self.crc >> 8
            print(self.cmd)
            self.serial.write(self.cmd)
        except Exception as e:
            show_error(e)
    
    #
    def set_relays(self):
        """
        Function for setting the desired Component
        """
        print(f"comps: {self.set}")
        for i in range(len(self.set)):
            check = self.set[i]
            if check != None:
                self.serial_write(check, state_request='on')
                time.sleep(0.02)
        self.loading()
    
    def up_button(self, state, wait = 0.0):
        """
        Function for simulating the UP button on the handlebar control
        Parameters:
            state = string with the desired state for the relay (on, off, flip)
            wait = float integer with the amount of time the desired state has to hold
        """
        self.cmd[3] = 30
        if state == 'on':
            self.cmd[4] = self.ON
        if state == 'off':
            self.cmd[4] = self.OFF
        self.cmd[5] = 0
        crc = pycrc.ModbusCRC(self.cmd[0:6])
        self.cmd[6] = crc & 0xFF
        self.cmd[7] = crc >> 8
        self.serial.write(self.cmd)
        print(f'UP {state}')
        time.sleep(wait)
        
    def down_button(self, state, wait = 0.0):
        """
        Function for simulating the DOWN button on the handlebar control
        Parameters:
            state = string with the desired state for the relay (on, off, flip)
            wait = float integer with the amount of time the desired state has to hold
        """
        self.cmd[3] = 31
        if state == 'on':
            self.cmd[4] = self.ON
        if state == 'off':
            self.cmd[4] = self.OFF
        self.cmd[5] = 0
        crc = pycrc.ModbusCRC(self.cmd[0:6])
        self.cmd[6] = crc & 0xFF
        self.cmd[7] = crc >> 8
        self.serial.write(self.cmd)
        print(f'UP {state}')
        time.sleep(wait)
        
    def wake_up(self):
        """
        Function for switching on the system by simulating a press on the display's button
        """
        self.cmd[3] = 29
        self.cmd[4] = self.ON
        self.cmd[5] = 0
        crc = pycrc.ModbusCRC(self.cmd[0:6])
        self.cmd[6] = crc & 0xFF
        self.cmd[7] = crc >> 8
        self.serial.write(self.cmd)
        print('WAKE UP ON')
        time.sleep(3)
        self.cmd[4] = self.OFF
        crc = pycrc.ModbusCRC(self.cmd[0:6])
        self.cmd[6] = crc & 0xFF
        self.cmd[7] = crc >> 8
        self.serial.write(self.cmd)
        print('WAKE UP OFF')
        time.sleep(2)
    
    def walk_mode(self):
        """
        Function for getting the system into walk mode and holding the pushing aid function for 10 seconds
        """
        self.up_button('on', 1)
        self.up_button('off', 0.5)
        self.up_button('on', 10)
        self.up_button('off')
                
    def loading(self):
        """
        Function that sends the progress value for the loading bar on one frontend's config card
        """
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
        self.bus = ManualRead()
        self.progress = 0
        self.combinations:list[list[int | None]] = []
        self.test:list[str] = []
        self.results = {}
        
    def connect(self):
        self.accept()
        self.reset_vars()
    
    def reset_vars(self):
        """
        Function for reseting all the run variables and the relays on the Modbus RTU Relay.
        """
        self.running = True
        self.send_master()
        self.modbus.reset_all()
        self.test.clear()
        self.combinations.clear()
        self.results.clear()
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
                self.reset_vars()
            if type == "back":
                self.test.pop(len(self.test)-1)
            if type == "auto":
                self._send(type, None)
                print("Automatisierter Durchlauf")
                self.test.append(type)
                print(self.test)
            if type == "manuell":
                print("Manueller Durchlauf der Kombinatoriken")
                self._send(type, None)
                self.test.append(type)
                print(self.test)
            if type == "konfig":
                self._send(type, None)
                print("Test über Konfig-File")
                self.test.append(type)
                print(self.test)
            if type == "manuell_comp":
                print("Manuelle Komp. Auswahl")
                self.test.append(type)
                print(self.test)
            if type == "set_combinations":
                print("set konfig")
                combinations = text_data_json["comb"]
                self.set_Relay(combinations)
            if type == "Konfig-File":
                print("Konfig-File recieved")
                konfig = text_data_json["text"]
                f = open("komp_pruefstand/static/Konfig.txt", "w")
                f.write(konfig)
                f.close()
                self.check_konfig_file()
            if type == "Master-File":
                print("Master-File recieved")
                master = text_data_json["text"]
                f = open("komp_pruefstand/static/Komponenten.yaml", "w")
                f.write(master)
                f.close()
                self.send_master()
            if type == "next":
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
        print('sending master')
        try:
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
                data = yaml.safe_load(f)
            self._send("components_names", data)
        except Exception as e:
            show_error(e)
    
    def run_progress(self):
        """
        Function for sending a countup to the client for displaying the progress to the user from 1 to 100
        """
        for x in range(1, 100):
            time.sleep(0.016)
            self._send("progress", x)
    
    def wake_and_walk(self):
        """
        Function for switching on the system and start the walking aid in one command
        """
        self.modbus.wake_up()
        self.modbus.walk_mode()
    
    def send_progress(self, index:int, konfigquantity:int):
        run_progress = Thread(target = self.run_progress, name="runlocalscript")
        wake_and_walk = Thread(target = self.wake_and_walk, name="runlocalscript")
        try:
            run_progress.start()
            #wake_and_walk.start()
            #time.sleep(7)
            self.results[index] = self.bus.read()
            self._send("progress", 100)
            if index != konfigquantity:
                self._send("next", None)
            if index == konfigquantity:
                self.check_results()
                print('Alle Kombinatoriken geschalten')
                self._send("done", None)
        except Exception as e:
            show_error(e)
    
    def set_Relay(self, combinations):
        comb = []
        try:
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
                data = yaml.safe_load(f)
                for combination in combinations:
                    print(combination)
                for combination in combinations:
                    for name in data:
                        if combination[name] != None:
                            comb.append(data[name][combination[name]]['relay'])
                        else:
                            comb.append(None)
                    self.combinations.append(comb)
                    comb = []
            self._send("combinations", self.combinations)
            self.run_combinations()
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
                            if len(combination) == 1 and combination[0] not in self.combinations:
                                self.combinations.append(combination[0])
                            else:
                                for c in range(len(combination)):
                                    if combination[c] not in self.combinations:
                                        self.combinations.append(combination[c])
                    print(f'\nAnzahl der Kombinationen: {len(self.combinations)}')
                    self._send("combinations", self.combinations)
                    self._send("konfigquantity", len(self.combinations))
                    self.run_combinations()
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
            if comp[0] == 'Ladegerät' or comp[0] == 'Service Dongle':
                comp[0] = 'Ladegerät/Service Dongle'
            if komma != -1:
                variants_name = [''] * len(konfig[comp[0]])
                variants_serial = [''] * len(konfig[comp[0]])
                choices = [x.strip() for x in comp[1].split(',')]
                if comp[0] == 'Battery' or comp[0] == 'Range EXT':
                    choices = self.check_kWh(choices)
                choices = list(set(choices))
                comp = comp[0]
                for i in range(len(konfig[comp])):
                    variants_name[i] = str(konfig[comp][i]['name'])   #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
                    variants_serial[i] = konfig[comp][i]['serial']   #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
                print(f'Anzahl Wahl {comp}: {len(choices)}')
                odds = []
                for name in range(len(choices)):
                    if choices[name].strip() not in variants_name and choices[name].strip() not in variants_serial:
                        odds.append((choices[name].strip()))
                if len(odds) != 0:
                    if len(odds) <= 1:
                        num = 'sind'
                        num1 = 'ist'
                    else:
                        num = 'ist'
                        num1 = 'sind'
                    print(f'Davon {num} aber nur {len(choices) - len(odds)} gültig.')
                    print(f'{comp} {odds} {num1} ungültig')
                    odds.append(comp)
                    self._send("odds", odds)
                f = {'name': [], 'serial': []}
                for index in range(len(konfig[comp])):
                    f['name'].append(str(konfig[comp][index]['name']))
                    f['serial'].append(konfig[comp][index]['serial'])
                for i in range(len(choices)):
                    double_serial, double_name = False, False
                    for index in range(len(konfig[comp])):
                        n = str(konfig[comp][index]['name'])
                        s = konfig[comp][index]['serial']
                        nc = f['name'].count(choices[i].strip())
                        sc = f['serial'].count(choices[i].strip())
                        if n == choices[i].strip() and not double_name:
                            relay.append((konfig[comp][index]["relay"]))
                            print(f'{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
                            if nc > 1:
                                double_name = True
                                break
                        if s == choices[i].strip() and not double_serial:
                            relay.append((konfig[comp][index]["relay"]))
                            print(f'{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
                            if sc > 1:
                                double_serial = True
                                break
                relay.sort()
                relays[comp] = list(relay)
            elif comp[1] != 'None':
                if comp[0] == 'Battery' or comp[0] == 'Range EXT':
                    comp[1] = self.check_kWh(comp[1])
                if comp[0] == 'Ladegerät' or comp[0] == 'Service Dongle':
                    comp[0] = 'Ladegerät/Service Dongle'
                for name in konfig[comp[0]]:
                    if str(name['name']) == comp[1]:
                        r = name['relay']
                    if name['serial'] == comp[1]:
                        r = name['relay']
                relays[comp[0]] = [r]
                print(f'{comp[0]}, {comp[1]} hat Relay: {r}')
                r = None
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
        for displaying the current configuration to the user.
        """
        try:
            self._send("progress", 0)
            if "auto" in self.test:
                for index, combination in enumerate(self.combinations, start=1):
                    print(f'Combination: {index}: {combination}')
                    self._send("testnum", index)
                    for rel in range(len(combination)):
                        if combination[rel] != None:
                            self.modbus.serial_write(id=combination[rel]-1, state_request='on')
                            time.sleep(0.02)
                    self.send_progress(index, len(self.combinations))
                    time.sleep(0.5)
                    self.modbus.reset_all()
                    self._send("progress", 0)
            if "manuell" in self.test:
                if self.index != len(self.combinations) + 1:
                    print(self.index, len(self.combinations))
                    combination = self.combinations[self.index - 1]
                    print(f'Combination: {self.index}: {combination}')
                    self._send("testnum", self.index)
                    for rel in range(len(combination)):
                        if combination[rel] != None:
                            self.modbus.serial_write(combination[rel]-1, 'on')
                            time.sleep(0.02)
                    self.send_progress(self.index, len(self.combinations))
                    time.sleep(0.5)
                    self.index += 1
                    self.modbus.reset_all()
        except Exception as e:  
            show_error(e)
    
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
                #serial = bool(re.search(r'\d', t))
                digit = bool(re.search(r'\d', t))
                if not digit:
                    if choice[-4:] != ' kWh':
                        k = choice.find('k')
                        #print(f'Index of k: {battery.find("k")}')
                        choice = choice[:k] + ' ' + choice[k:]
                        choices[ind] = choice
                    # if t != ' kWh':
                    #     k = choice.find('k')
                    #     #print(f'Index of k: {battery.find("k")}')
                    #     choice = choice[:k] + ' ' + choice[k:]
                    #     choices[ind] = choice
        else:
            x = choices[-4:]
            digit = bool(re.search(r'\d', x))
            if not digit:
                if x != ' kWh':
                    k = choices.find('k')
                    #print(f'Index of k: {choices.find("k")}')
                    choices = choices[:k] + ' ' + choices[k:]
            # serial = bool(re.search(r'\d', x))
            # if not serial:
            #     if x != ' kWh':
            #         k = choices.find('k')
            #         #print(f'Index of k: {choices.find("k")}')
            #         choices = choices[:k] + ' ' + choices[k:]
        return choices
    
    def check_results(self):
        for test in self.results:
            print(f'Test {test}:\n{self.results[test]}')
            print('---------------------')

    def stop(self):
        self.running = False
        
#Thomas Zengerle -> kabel
#Matthias Schoppe -> can
#Kundennummer inning 3006166
#Buchungsnummer: P/00026620/000002 --> PSP Element bei BANF
#Manuela Kabelbaum Bestellung mit PSP Element