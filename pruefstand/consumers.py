import asyncio
import json
import sys, os
import serial
import pruefstand.pycrc as pycrc
import time
import yaml
import numpy as np
import itertools
import re
import mimetypes
import glob
import pandas as pd
from datetime import datetime as dt
from pruefstand import pycrc
from enum import Enum
from django.http import JsonResponse
from threading import Thread
from typing import Literal
from komp_pruefstand.views import download_file
from channels.generic.websocket import AsyncWebsocketConsumer
from .PCAN.libpcanbasic.examples.console.Python.ManualRead.ManualRead import ManualRead


def show_error(exception):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1] # type: ignore
    print(exc_type, fname, exc_tb.tb_lineno, exception) # type: ignore

class ModBusRelay():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Definierung des Ausgangs und der Baudrate fuer Bus
        self.serial = serial.Serial("/dev/ttyS0",9600,timeout=1)
        # Array fuer RS485-Nachricht
        self.cmd = [0x01, 0x05, 0, 0, 0, 0, 0, 0]
        # Leerer Array zum abspeichern der zu schaltenden Relais
        self.set:list[int | None] = [None] * 6
        # Byte zum Einschalten eines Relais
        self.ON = 0xFF
        # Byte zum Ausschalten eines Relais
        self.OFF = 0x00
        # Byte fuer einen Flip eines Relais (on <-> off)
        self.FLIP = 0x55
        
    # Alle Relais aus: 01 05 00 FF 00 00 FD FA
    async def reset_all(self):
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
            self.serial.write(self.cmd) # type: ignore
            await asyncio.sleep(0.1)
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
    
    def crc16(self):
        """
        Function for calculating the cyclic redundancy checksum
        """
        crc = pycrc.ModbusCRC(self.cmd[0:6])
        self.cmd[6] = crc & 0xFF
        self.cmd[7] = crc >> 8
        self.serial.write(self.cmd) # type: ignore
        #print(self.cmd)
    
    async def up_button(self, state, wait = 0.0):
        """
        Function for simulating the UP button on the handlebar control
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
            await asyncio.sleep(wait)
        except Exception as e:
            show_error(e)
        
    async def down_button(self, state, wait = 0.0):
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
            await asyncio.sleep(wait)
        except Exception as e:
            show_error(e)
        
    async def wake_up(self):
        """
        Function for switching on the system by simulating a press on the display's button
        """
        try:
            self.cmd[3] = 30
            self.cmd[4] = self.ON
            self.cmd[5] = 0
            self.crc16()
            print('WAKE UP ON')
            await asyncio.sleep(3)
            self.cmd[4] = self.OFF
            self.crc16()
            print('WAKE UP OFF')
            await asyncio.sleep(2)
        except Exception as e:
            show_error(e)
        
    async def walk_mode(self):
        """
        Function for getting the system into walk mode and holding the pushing aid function for 10 seconds
        """
        await self.up_button('on', 1)
        await self.up_button('off', 0.5)
        await self.up_button('on', 10)
        await self.up_button('off')

####################################################################################################################

# Klasse für Kommunikation zwischen Server und Client
class TestConsumer(AsyncWebsocketConsumer):
    test:list[str] = []
    combinations:list[tuple] = []
    index = 1
    error_list = pd.DataFrame(pd.read_csv('/home/simonbader/Coding/Fehlerliste.csv', sep=';', dtype=str))
    group = 'tq'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Variable fuer 
        self.running = False
        # Variable zur Kommunikation mit 32CH-Relais-Block
        self.modbus = ModBusRelay()
        #self.combinations:list[list[int | None]] = []
        # self.combinations:list[tuple] = []
        # Array, in welchem die Nutzerwahl der Testart abgespeichert wird
        # self.test:list[str] = []
        # Dictionary zum abspeichern der CAN-Bus-Ueberwachungsergebnisse 
        self.results = {}
        self.path = '/home/simonbader/Coding/TestResults'
        self.filenames:list[str] = []
    
    # Funktion zum Aufbau der Websocket-Verbindung
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add(self.group, self.channel_name)  # type: ignore
        await self.reset_vars()

    async def websocket_accept(self, event):
        if event['id'] != self.channel_name:
            await self.send(text_data=event['message'])
    
    # Funktion zum Trennen der Websocket-Verbindung 
    async def disconnect(self, close_code):
        self.running = False
        await self.channel_layer.group_discard(self.group, self.channel_name)  # type: ignore
        
    # Funktion zum Zuruecksetzen aller Variablen welche im Laufe eines Tests benötigt werden
    async def reset_vars(self):
        """
        Function for reseting all the run variables and the relays on the Modbus RTU Relay.
        """
        self.test.clear()
        self.running = True
        await self.send_master()
        self.combinations.clear()
        self.results.clear()
        self.index = 1
        await self.modbus.reset_all()
        
    # Funktion zum Senden der Nachrichten an Client - verallgemeinert mit "Message" und "Value"
    async def _send(self, message, value = None):
        await self.send(text_data=json.dumps({message: value}))
        if message != 'master':
            await self.group_send(message, value)
        
    async def group_send(self, message, value = None):
        await self.channel_layer.group_send(self.group, {"type": "websocket.accept", 'message': json.dumps({message: value}), 'id' : self.channel_name}) # type: ignore
        
    # Alle Funktionen für die Kommunikation zwischen Client und Server
    async def receive(self, text_data):
        """
        Function for recieving and sending information between the server and the client and proceeding that information to the
        corresponding functions.
        """
        try:
            text_data_json = json.loads(text_data)
            type = text_data_json["type"]
            # Nutzer klickt auf Home-Button
            if type == "home":
                # self._send("home")
                await self._send("home")
                await self.reset_vars()
            # Nutzer klickt auf Zurueck-Button
            if type == "back":
                self.test.pop(len(self.test)-1)
            if type == "auto":
                print("Automatisierter Durchlauf")
                await self._send(type)
                self.test.append(type)
            if type == "manuell":
                print("Manueller Durchlauf der Kombinationen")
                await self._send(type)
                self.test.append(type)
            if type == "konfig":
                print("Test über Konfig-File")
                await self._send(type)
                self.test.append(type)
            if type == "manuell_comp":
                print("Manuelle Komp. Auswahl")
                self.test.append(type)
            if type == "set_combinations":
                print("set combinations")
                combinations = text_data_json["comb"]
                await self.set_Relay(combinations)
            if type == "Konfig-File":
                print("Konfig-File recieved")
                konfig = text_data_json["text"]
                f = open("komp_pruefstand/static/Konfig.txt", "w")
                f.write(konfig)
                f.close()
                await self.check_konfig_file()
            if type == "Master-File":
                print("Master-File recieved")
                master = text_data_json["text"]
                f = open("komp_pruefstand/static/Komponenten.yaml", "w")
                f.write(master)
                f.close()
                await self.send_master()
            if type == "next":
                await asyncio.sleep(0.05)
                self.index += 1
                await self.run_combinations() # type: ignore
            if type == "delete":
                os.remove(text_data_json["message"])
                await self.get_metadata()
            if type == "download":
                with open(f'{text_data_json["message"]}', 'rb') as f:
                    file = yaml.safe_load(f)
                filename = os.path.basename(text_data_json["message"])
                print(text_data_json["message"])
                await self._send("filename", filename)
                await asyncio.sleep(0.1)
                await self._send("download", file)
            if type == "stop":
                print("stop")
                self.stop()
        except Exception as e:
            show_error(e)
    
    # Funktion, welche das Master-Konfig-File an den Client sendet
    async def send_master(self):
        """
        Sends the Master-Config-File to the Client for displaying the possible choices to the user.
        """
        print('sending master')
        try:
            with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as f:
                self.master = yaml.safe_load(f)
            await self._send("master", self.master)
        except Exception as e:
            show_error(e)
    
    # Funktion, welche den Ladefortschritt an den Client sendet, damit dort der Ladebalken den Fortschritt des Tests anzeigen kann
    async def loading_bar(self):
        """
        Function for sending a countup to the client for displaying the progress to the user from 1 to 100
        """
        for x in range(1, 100):
            if self.running:
                await asyncio.sleep(0.17)
                await self._send("progress", x)
    
    async def wake_and_walk(self):
        """
        Function for switching on the system and start the walking aid in one command
        """
        await self.modbus.wake_up()
        await self.modbus.walk_mode()
    
    async def send_progress(self, index:int):
        component = {}
        for c in self.master:
            component[c] = ''
        try:
            asyncio.create_task(self.loading_bar())
            asyncio.create_task(self.wake_and_walk())
            await asyncio.sleep(7)
            self.results[f'Test{index}'] = await ManualRead().read(self.error_list)
            self.results[f'Test{index}']['Komponenten'] = component
            self.find_names(index)
            await self._send("progress", 100)
            if index == len(self.combinations):
                print('Alle Kombinatoriken geschalten')
                await self._send("done")
        except Exception as e:
            show_error(e)
    
    async def set_Relay(self, combinations):
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
                self.combinations.append(comb) # type: ignore
                comb = []
            await self._send("combinations", self.combinations)
            await self.run_combinations()
        except Exception as e:
            show_error(e)
        
    async def run_combinations(self):
        """
        Function that runs through the user selected configurations - according to the choice of 'auto' or 'manual' - and sets the relays of an
        individual combination in the list of all possible combinations. It also sends the current number of the running combination to the client
        for displaying the current configuration to the user.
        """
        try:
            print(self.test)
            if "auto" in self.test:
                await self._send("progress", 0)
                for index, combination in enumerate(self.combinations, start=1):
                    print(f'Combination: {index}: {combination}')
                    await self._send("testnum", index)
                    for rel in range(len(combination)):
                        if combination[rel] != None:
                            self.modbus.set_relays(combination[rel], 'on')
                            await asyncio.sleep(0.02)
                    await self.send_progress(index)
                    await asyncio.sleep(0.5)
                    await self.modbus.reset_all()
                    await self._send("progress", 0)
            if "manuell" in self.test:
                await self._send("progress", 0)
                print(self.combinations)
                if self.index != len(self.combinations) + 1:
                    combination = self.combinations[self.index - 1]
                    print(f'Combination: {self.index}: {combination}')
                    await self._send("testnum", self.index)
                    for rel in range(len(combination)):
                        if combination[rel] != None:
                            self.modbus.set_relays(combination[rel], 'on')
                            await asyncio.sleep(0.02)
                    await self.send_progress(self.index)
                    await asyncio.sleep(0.5)
                    await self.modbus.reset_all()
                    index = 0
            if index or self.index == len(self.combinations):
                filename = dt.now().strftime("%Y_%m_%d-%H_%M_%S")
                with open(f'{self.path}/TestErgebnis_{filename}.yaml', 'w') as file:
                    file.write(yaml.dump(self.results, indent=4, allow_unicode=True)) 
                await self.get_metadata()
                # with open(f'/home/simonbader/Coding/TestResults/TestErgebnis{len(files)+1}.yaml', 'r') as file:
                #     results = yaml.safe_load(file)
        except Exception as e:
            show_error(e)
    
    async def check_konfig_file(self):
        """
        Function that strips the by the user uploaded Konfig-File in category- and component-names and passes that information to the 'parser-function' for further analysis.
        Sends the recieved combination-possibilities to the client and passes them to the 'run_combinations-function'.
        """
        #self.combinations:list[tuple] = []
        try:
            await self._send('Upload erfolgreich')
            with open(f"komp_pruefstand/static/Konfig.txt", "r") as t:
                lines = t.readlines()
                breaks = []
                konfig_count = 1
                for index, line in enumerate(lines):
                    l = line.find('\n')
                    if l == 0:
                        breaks.append(index)
                        konfig_count += 1
                if konfig_count == 1:
                    c = await self.parser(lines) # type: ignore
                    self.combinations = c or []
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
                        combination = (await self.parser(konfigs[f'Konfig{k+1}'])) or []
                        if len(combination) == 1 and combination[0] not in self.combinations:
                            self.combinations.append(combination[0])
                        else:
                            for c in range(len(combination)):
                                if combination[c] not in self.combinations:
                                    self.combinations.append(combination[c])
                print(f'\nAnzahl der Kombinationen: {len(self.combinations)}')
                await self._send("combinations", self.combinations)
                await self._send("konfigquantity", len(self.combinations))
                await self.run_combinations()
        except Exception as e:
            show_error(e)
            
    async def parser(self, lines:list[str]):
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
                        variants_serial[i] = self.master[comp][i]['serial']   #Array mit Seriennummer der Unterkomponenten, von Komp, wo Auswahl > 1
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
                        await self._send("odds", odds)
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
                        comp[1] = self.check_kWh(comp[1])  # type: ignore
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
                        choices[ind] = choice  # type: ignore
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
                            if name['name'] == 'Ladegerät':
                                del self.results[f'Test{index}']['Komponenten']['Ladegerät/Service Dongle']
                                self.results[f'Test{index}']['Komponenten']['Ladegerät'] = name['serial']
                                break
                            if name['name'] == 'Service Dongle':
                                component = 'Service Dongle'
                                del self.results[f'Test{index}']['Komponenten']['Ladegerät/Service Dongle']
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
            
    async def get_metadata(self):
        try:
            self.filenames = sorted(glob.glob(self.path + '/*.yaml'))
            self.filenames.reverse()
            metadata = {}
            metadata['TestResult'] = {}
            results = {}
            for i, filename in enumerate(self.filenames):
                results[f'{i}'] = {}
                results[f'{i}']['filename'] = self.filenames[i]
                results[f'{i}']['created_at'] = os.path.getatime(filename)
            await self._send("results", results)
        except Exception as e:
            show_error(e)

    def stop(self):
        self.running = False
        
#Thomas Zengerle -> kabel
#Matthias Schoppe -> can
#Kundennummer inning 3006166
#Buchungsnummer: P/00026620/000002 --> PSP Element bei BANF
#Manuela Kabelbaum Bestellung mit PSP Element
# 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