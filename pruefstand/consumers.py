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
        # Definierung des Ausgangs und der Baudrate fuer Bus
        self.serial = serial.Serial("/dev/ttyS0",9600,timeout=1)
        # Array fuer RS485-Nachricht
        self.cmd = [0x01, 0x05, 0, 0, 0, 0, 0, 0]
        # Array mit Strings der Komponenten
        self.comps = ["Motor", "Display", "Battery", "Charger", "Range EXT", "Service Dongle"]
        # Leerer Array zum abspeichern der zu schaltenden Relais
        self.set:list[int | None] = [None] * 6
        # Byte zum Einschalten eines Relais
        self.ON = 0xFF
        # Byte zum Ausschalten eines Relais
        self.OFF = 0x00
        # Byte fuer einen Flip eines Relais (on <-> off)
        self.FLIP = 0x55
        
    # Alle Relais aus: 01 05 00 FF 00 00 FD FA
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
    
    # Funktion zum Schreiben der Nachrichten auf BUS
    def set_relays(self, id:int | None, state_request: Literal['on', 'off', 'flip']):
        """
        Function for writing on the CAN-Bus to the Modbus RTU Relay and setting the given relays.
        Parameters:
            id = number of the relay to set
            state = string with the desired state for the relay (on, off, flip)
        """
        try:
            self.cmd[2] = 0
            self.cmd[3] = int(format(id if id == None else id-1, '#04x'), 16)
            if state_request == 'on':
                self.cmd[4] = self.ON
            if state_request == 'off':
                self.cmd[4] = self.OFF
            if state_request == 'flip':
                self.cmd[4] = self.FLIP
            self.cmd[5] = 0
            self.crc16()
        except Exception as e:
            show_error(e)
    
    def up_button(self, state, wait = 0.0):
        """
        Function for simulating the UP button on the handlebar control
        Parameters:
            state = string with the desired state for the relay (on, off, flip)
            wait = float integer with the amount of time the desired state has to hold
        """
        try:
            self.cmd[3] = 30
            if state == 'on':
                self.cmd[4] = self.ON
            if state == 'off':
                self.cmd[4] = self.OFF
            self.cmd[5] = 0
            self.crc16()
            print(f'UP {state}')
            time.sleep(wait)
        except Exception as e:
            show_error(e)
        
    def down_button(self, state, wait = 0.0):
        """
        Function for simulating the DOWN button on the handlebar control
        Parameters:
            state = string with the desired state for the relay (on, off, flip)
            wait = float integer with the amount of time the desired state has to hold
        """
        try:
            self.cmd[3] = 31
            if state == 'on':
                self.cmd[4] = self.ON
            if state == 'off':
                self.cmd[4] = self.OFF
            self.cmd[5] = 0
            self.crc16()
            print(f'UP {state}')
            time.sleep(wait)
        except Exception as e:
            show_error(e)
        
    def wake_up(self):
        """
        Function for switching on the system by simulating a press on the display's button
        """
        try:
            self.cmd[3] = 29
            self.cmd[4] = self.ON
            self.cmd[5] = 0
            self.crc16()
            print('WAKE UP ON')
            time.sleep(3)
            self.cmd[4] = self.OFF
            self.crc16()
            print('WAKE UP OFF')
            time.sleep(2)
        except Exception as e:
            show_error(e)
    
    def crc16(self):
        crc = pycrc.ModbusCRC(self.cmd[0:6])
        self.cmd[6] = crc & 0xFF
        self.cmd[7] = crc >> 8
        self.serial.write(self.cmd)
        print(self.cmd)
    
    def walk_mode(self):
        """
        Function for getting the system into walk mode and holding the pushing aid function for 10 seconds
        """
        self.up_button('on', 1)
        self.up_button('off', 0.5)
        self.up_button('on', 10)
        self.up_button('off')

####################################################################################################################

# Klasse für Kommunikation zwischen Server und Client
class TestConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Variable fuer 
        self.running = False
        # Variable zur Kommunikation mit 32CH-Relais-Block
        self.modbus = ModBusRelay()
        # Variable zur Ueberwachung des CAN-Bus

        # Dictionary zum Abspeichern der Kombinationsmöglichkeiten
        #self.combinations:list[list[int | None]] = []
        self.combinations:list[tuple] = []
        # Array, in welchem die Nutzerwahl der Testart abgespeichert wird
        self.test:list[str] = []
        # Dictionary zum abspeichern der CAN-Bus-Ueberwachungsergebnisse
        self.results = {}
    
    # Funktion zum Aufbau der Websocket-Verbindung
    def connect(self):
        self.accept()
        self.reset_vars()
    
    # Funktion zum Trennen der Websocket-Verbindung
    def disconnect(self, close_code):
        self.running = False
        
    # Funktion zum Zuruecksetzen aller Variablen welche im Laufe eines Tests benötigt werden
    def reset_vars(self):
        """
        Function for reseting all the run variables and the relays on the Modbus RTU Relay.
        """
        self.test.clear()
        print(self.test)
        self.running = True
        self.send_master()
        self.combinations.clear()
        self.results.clear()
        self.index = 1
        self.modbus.reset_all()
        
    # Funktion zum Senden der Nachrichten an Client - verallgemeinert mit "Message" und "Value"
    def _send(self, message, value = None):
        self.send(text_data=json.dumps({message: value}))

    # Alle Funktionen für die Kommunikation zwischen Client und Server
    def receive(self, text_data):
        """
        Function for recieving and sending information between the server and the client and proceeding that information to the
        corresponding functions.
        """
        try:
            text_data_json = json.loads(text_data)
            type = text_data_json["type"]
            # Nutzer klickt auf Home-Button
            if type == "home":
                self._send("home")
                self.reset_vars()
                print(self.test)
                print("home")
            # Nutzer klickt auf Zurueck-Button
            if type == "back":
                self.test.pop(len(self.test)-1)
            if type == "auto":
                print("Automatisierter Durchlauf")
                self._send(type)
                self.test.append(type)
                print(self.test)
            if type == "manuell":
                print("Manueller Durchlauf der Kombinatoriken")
                self._send(type)
                self.test.append(type)
                print(self.test)
            if type == "konfig":
                print("Test über Konfig-File")
                self._send(type)
                self.test.append(type)
                print(self.test)
            if type == "manuell_comp":
                print("Manuelle Komp. Auswahl")
                self.test.append(type)
                print(self.test)
            if type == "set_combinations":
                print("set combinations")
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
                self.index += 1
                self.run_combinations()
            if type == "stop":
                print("stop")
                self.stop()
        except Exception as e:
            show_error(e)
    
    # Funktion, welche das Master-Konfig-File an den Client sendet
    def send_master(self):
        """
        Sends the Master-Config-File to the Client for displaying the possible choices to the user.
        """
        print('sending master')
        try:
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
                self.master = yaml.safe_load(f)
            self._send("components_names", self.master)
        except Exception as e:
            show_error(e)
    
    # Funktion, welche den Ladefortschritt an den Client sendet, damit dort
    # der Ladebalken den Fortschritt des Tests anzeigen kann
    def loading_bar(self):
        """
        Function for sending a countup to the client for displaying the progress to the user from 1 to 100
        """
        for x in range(1, 100):
            if self.running:
                time.sleep(0.15)
                self._send("progress", x)
    
    def wake_and_walk(self):
        """
        Function for switching on the system and start the walking aid in one command
        """
        self.modbus.wake_up()
        self.modbus.walk_mode()
    
    def send_progress(self, index:int):
        loading_bar = Thread(target = self.loading_bar, name="runlocalscript")
        wake_and_walk = Thread(target = self.wake_and_walk, name="runlocalscript")
        component = {}
        for c in self.master:
            component[c] = ''
        try:
            loading_bar.start()
            wake_and_walk.start()
            time.sleep(7)
            self.results[f'Test{index}'] = ManualRead().read()
            self.results[f'Test{index}']['Komponenten'] = component
            self.find_names(index)
            self._send("progress", 100)
            if index != len(self.combinations):
                self._send("next", None)
            if index == len(self.combinations):
                #self.check_results()
                print('Alle Kombinatoriken geschalten')
                self._send("done")
        except Exception as e:
            show_error(e)
    
    def set_Relay(self, combinations):
        comb = []
        try:
            #with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
            #data = yaml.safe_load(f)
            for combination in combinations:
                print(combination)
            for combination in combinations:
                #for name in data:
                for name in self.master:
                    if combination[name] != None:
                        comb.append(self.master[name][combination[name]]['relay'])
                    else:
                        comb.append(None)
                self.combinations.append(comb)
                comb = []
            self._send("combinations", self.combinations)
            self.run_combinations()
        except Exception as e:
            show_error(e)
        
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
                            self.modbus.set_relays(combination[rel], 'on')
                            time.sleep(0.02)
                    self.send_progress(index)
                    time.sleep(0.5)
                    self.modbus.reset_all()
                    self._send("progress", 0)
            if "manuell" in self.test:
                if self.index != len(self.combinations) + 1:
                    combination = self.combinations[self.index - 1]
                    print(f'Combination: {self.index}: {combination}')
                    self._send("testnum", self.index)
                    for rel in range(len(combination)):
                        if combination[rel] != None:
                            self.modbus.set_relays(combination[rel], 'on')
                            time.sleep(0.02)
                    self.send_progress(self.index)
                    time.sleep(0.5)
                    self.modbus.reset_all()
                    index = 0
            print(index, self.index, len(self.combinations))
            if index or self.index == len(self.combinations):
                with open('komp_pruefstand/static/can.yaml', 'w') as file:
                    file.write(yaml.dump(self.results, indent=4, allow_unicode=True))
                with open('komp_pruefstand/static/can.yaml', 'r') as file:
                    results = yaml.safe_load(file)
                self._send("results", results)
        except Exception as e:
            show_error(e)
    
    def check_konfig_file(self):
        """
        Function that strips the by the user uploaded Konfig-File in category- and component-names and passes that information to the 'parser-function' for further analysis.
        Sends the recieved combination-possibilities to the client and passes them to the 'run_combinations-function'.
        """
        #self.combinations:list[tuple] = []
        try:
            self._send('Upload erfolgreich')
            with open(f"komp_pruefstand/static/Konfig.txt", "r") as t:
                print(self.master)
                lines = t.readlines()
                breaks = []
                konfig_count = 1
                for index, line in enumerate(lines):
                    l = line.find('\n')
                    if l == 0:
                        breaks.append(index)
                        konfig_count += 1
                if konfig_count == 1:
                    self.combinations = self.parser(lines)
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
                        combination = self.parser(konfigs[f'Konfig{k+1}'])
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
            
    def parser(self, lines:list[str]):
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
        try:
            relays = {}
            for key in list(self.master.keys()):
                relays[key] = None
            for line in lines:
                string = line.rstrip()
                relay = []
                comp = [x.strip() for x in string.split(':', line.find(':'))]
                if comp[0] == 'Range Ext' or comp[0] == 'RangeExt':
                    comp[0] = 'Range EXT'
                if comp[0] == 'Ladegerät' or comp[0] == 'Service Dongle':
                    comp[0] = 'Ladegerät/Service Dongle'
                if line.find(",") != -1:
                    variants_name = [''] * len(self.master[comp[0]])
                    variants_serial = [''] * len(self.master[comp[0]])
                    choices = [x.strip() for x in comp[1].split(',')]
                    if comp[0] == 'Battery' or comp[0] == 'Range EXT':
                        choices = self.check_kWh(choices)
                    choices = list(set(choices))
                    comp = comp[0]
                    for i in range(len(self.master[comp])):
                        variants_name[i] = str(self.master[comp][i]['name'])  #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
                        variants_serial[i] = self.master[comp][i]['serial']   #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
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
                    for index in range(len(self.master[comp])):
                        f['name'].append(str(self.master[comp][index]['name']))
                        f['serial'].append(self.master[comp][index]['serial'])
                    for i in range(len(choices)):
                        double_serial, double_name = False, False
                        for index in range(len(self.master[comp])):
                            n = str(self.master[comp][index]['name'])
                            s = self.master[comp][index]['serial']
                            nc = f['name'].count(choices[i].strip())
                            sc = f['serial'].count(choices[i].strip())
                            if n == choices[i].strip() and not double_name:
                                relay.append((self.master[comp][index]["relay"]))
                                print(f'{comp}, {choices[i]} hat Relay: {self.master[comp][index]["relay"]}')
                                if nc > 1:
                                    double_name = True
                                    break
                            if s == choices[i].strip() and not double_serial:
                                relay.append((self.master[comp][index]["relay"]))
                                print(f'{comp}, {choices[i]} hat Relay: {self.master[comp][index]["relay"]}')
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
                    for name in self.master[comp[0]]:
                        if str(name['name']) == comp[1]:
                            relays[comp[0]] = [name['relay']]
                        if name['serial'] == comp[1]:
                            relays[comp[0]] = [name['relay']]
                    print(f'{comp[0]}, {comp[1]} hat Relay: {relays[comp[0]]}')
            print(f'Relays zu schalten: {relays}\n')
            l = []
            for key in relays:
                if relays[key] != None:
                    l.append(relays[key])
                else:
                    l.append([None])
            return list(itertools.product(*l))
        except Exception as e:
            show_error(e)
    
    def check_kWh(self, choices: list[str] | str):
        """
        Function for checking the Konfig-File on wrong written 'kWh' unit for comparison with Master-Konfig-File.
        
        Returns string with corrected written unit
        
        Parameters:
            choices = string of current component choices (Motor, Display, ect.)
        """
        if type(choices) != str:
            for ind, choice in enumerate(choices):
                t = choice[-4:]
                digit = bool(re.search(r'\d', t))
                if not digit:
                    if choice[-4:] != ' kWh':
                        k = choice.find('k')
                        choice = choice[:k] + ' ' + choice[k:]
                        choices[ind] = choice
        else:
            x = choices[-4:]
            digit = bool(re.search(r'\d', x))
            if not digit:
                if x != ' kWh':
                    k = choices.find('k')
                    choices = choices[:k] + ' ' + choices[k:]
        return choices
    
    def check_results(self):
        for test in self.results:
            print(f'Test {test}:\n{self.results[test]}')
            print('---------------------')
    
    def find_names(self, index):
        for relay in self.combinations[index-1]:
            for component in self.master:
                for name in self.master[component]:
                    if relay == name['relay']:
                        if name['name'] != None:
                            self.results[f'Test{index}']['Komponenten'][component] =  name['name']
                            break
                        else:
                            self.results[f'Test{index}']['Komponenten'][component] =  name['serial']
                            break
                else:
                    continue
                break
            else:
                continue

    def stop(self):
        self.running = False
        
#Thomas Zengerle -> kabel
#Matthias Schoppe -> can
#Kundennummer inning 3006166
#Buchungsnummer: P/00026620/000002 --> PSP Element bei BANF
#Manuela Kabelbaum Bestellung mit PSP Element
# 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