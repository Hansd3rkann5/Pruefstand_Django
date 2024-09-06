import asyncio
import json
import sys, os
from argon2 import Type
import serial
import pruefstand.pycrc as pycrc
import yaml
import itertools
import re
import glob
import pandas as pd
from datetime import datetime as dt
from pruefstand import pycrc
from enum import Enum
from typing import Literal
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
        await self.up_button('on', 12.5)
        await self.up_button('off')

####################################################################################################################

# Klasse für Kommunikation zwischen Server und Client
class TestConsumer(AsyncWebsocketConsumer):
    #Klassenvariablen
    test:list[str] = []
    index = 1
    error_list = pd.DataFrame(pd.read_csv('/home/simonbader/Coding/Fehlerliste.csv', sep=';', dtype=str))
    group = 'tq'
    test_running = False
    combinations:list[tuple] = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Instanzvariablen
        self.running = False
        self.modbus = ModBusRelay()
        self.results = {}
        self.results_list = {}
        self.path = '/home/simonbader/Coding/TestResults'
        self.filenames:list[str] = []
    
    async def connect(self):
        self.client_id = self.scope['client'][1]
        await self.accept()
        await self.channel_layer.group_add(self.group, self.channel_name)  # type: ignore
        await self.reset_vars(self.scope['client'])

    async def websocket_accept(self, event):
        if event['id'] != self.channel_name:
            await self.send(event['message'])
            await self.reset_vars()
    
    async def disconnect(self, close_code):
        self.running = False
        await self.channel_layer.group_discard(self.group, self.channel_name)  # type: ignore
        
    async def reset_vars(self, client = None):
        """
        Function for reseting all the run variables and the relays on the Modbus RTU Relay.
        """
        if client != None:
            if client[1] == self.client_id or client[0][:3] == '127':
                await self.send_master(client)
                self.results.clear()
                if not TestConsumer.test_running:
                    await self.modbus.reset_all()
                    TestConsumer.combinations.clear()
                    TestConsumer.index = 1
                TestConsumer.test.clear()
                print(TestConsumer.index, TestConsumer.combinations, TestConsumer.test)
        
    async def _send(self, message, value = None):
        await self.send(text_data=json.dumps({message: value}))
        if message != 'master' or message != 'false upload':
            await self.group_send(message, value)
        
    async def group_send(self, message, value = None):
        await self.channel_layer.group_send(self.group, {"type": "websocket.accept", 'message': json.dumps({message: value}), 'id' : self.channel_name}) # type: ignore
        
    async def receive(self, text_data):
        """
        Function for recieving and sending information between the server and the client and proceeding that information to the
        corresponding functions.
        """
        try:
            text_data_json = json.loads(text_data)
            type = text_data_json["type"]
            if type == "home":
                await self._send("home")
                await self._send("master", self.master)
                await self.reset_vars(self.scope['client'])
            if type == "back":
                TestConsumer.test.pop(len(TestConsumer.test)-1)
            if type == "auto":
                print("Automatisierter Durchlauf")
                await self._send(type)
                TestConsumer.test.append(type)
            if type == "manuell":
                print("Manueller Durchlauf der Kombinationen")
                await self._send(type)
                TestConsumer.test.append(type)
            if type == "konfig":
                print("Test über Konfig-File")
                await self._send(type)
                TestConsumer.test.append(type)
            if type == "manuell_comp":
                print("Manuelle Komp. Auswahl")
                TestConsumer.test.append(type)
            if type == "set_combinations":
                print("set combinations")
                combinations = text_data_json["comb"]
                await self.set_combinations(combinations)
            if type == "Konfig-File":
                print("Konfig-File recieved")
                konfig = text_data_json["text"]
                check = konfig.strip('\n').find(':')
                if konfig[:check] in self.comps:
                    with open("komp_pruefstand/static/Konfig.txt", "w") as txt:
                        txt.write(konfig)
                    await self.check_konfig_file()
                else:
                    await self._send("false upload")
            if type == "Master-File":
                print("Master-File recieved")
                master = text_data_json["text"]
                dots = master.strip('\n').find(':')
                if master[:dots] in self.comps:
                    with open("komp_pruefstand/static/Master.yaml", "w") as txt:
                        txt.write(master)
                    await self.send_master(None)
                if master[:6] == 'Fehler':
                    with open("/home/simonbader/Coding/Fehlerliste.csv", "w") as csv_list:
                        csv_list.write(master)
                if master[:dots] not in self.comps or master[:6] != 'Fehler':
                    await self._send("false upload")
            if type == "next":
                await asyncio.sleep(0.05)
                TestConsumer.index += 1
                await self.run_combinations() # type: ignore
            if type == "delete":
                for x in self.results_list:
                    if self.results_list[x]['filename'] == text_data_json["message"]:
                        self.results_list.pop(x)
                        break
                os.remove(text_data_json["message"])
                await self._send("results", self.results_list)
            if type == "download":
                with open(f'{text_data_json["message"]}', 'rb') as txt:
                    file = yaml.safe_load(txt)
                filename = os.path.basename(text_data_json["message"])
                await self._send("filename", filename)
                await asyncio.sleep(0.1)
                await self._send("download", file)
            if type == "stop":
                print("stop")
                self.stop()
        except Exception as e:
            show_error(e)
    
    async def send_master(self, client):
        """
        Sends the Master-Config-File to the Client for displaying the possible choices to the user.
        """
        print('sending master')
        try:
            with open(f"komp_pruefstand/static/Master.yaml", "r") as f:
                self.master = yaml.safe_load(f)
            await self.send(text_data=json.dumps({"master": self.master, "running": TestConsumer.test_running}))
            self.comps = list(self.master.keys())
            self.comps.extend(['Ladegerät', 'Service Dongle'])
        except Exception as e:
            show_error(e)
    
    async def loading_bar(self):
        """
        Function for sending a countup to the client for displaying the progress to the user from 1 to 100
        """
        for x in range(1, 100):
            if TestConsumer.test_running:
                await asyncio.sleep(0.18)
                await self._send("progress", x)
    
    async def wake_and_walk(self):
        """
        Function for switching on the system and start the walking aid in one command
        """
        await self.modbus.wake_up()
        await self.modbus.walk_mode()
    
    async def send_progress(self, index:int):
        """
        Function that starts tracing the CAN-Bus communication on the system and safes each trace into an entry of the result dicitonary.
        """
        component = {}
        for c in self.master:
            component[c] = ''
        try:
            asyncio.create_task(self.loading_bar())
            asyncio.create_task(self.wake_and_walk())
            self.results[f'Konfig.{index}'], error = await ManualRead().read(TestConsumer.error_list)
            self.results[f'Konfig.{index}']['Komponenten'] = component
            self.find_names(index)
            await self._send("progress", 100)
            if error:
                self.results['EMCY'] = True
            if index == len(TestConsumer.combinations):
                print('Alle Kombinatoriken geschalten')
                TestConsumer.test_running = False
                await self._send("done")
        except Exception as e:
            await self._send("done")
            show_error(e)
    
    async def set_combinations(self, combinations):
        """
        Function that sets the relays of a combinations when the client starts a test via the manuall component choice.
        """
        comb = []
        try:
            for combination in combinations:
                print(combination)
            for combination in combinations:
                for name in self.master:
                    if combination[name] != None:
                        comb.append(self.master[name][combination[name]]['relay'])
                    else:
                        comb.append(None)
                TestConsumer.combinations.append(comb) # type: ignore
                comb = []
            await self._send("combinations", TestConsumer.combinations)
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
            TestConsumer.test_running = True
            if "auto" in TestConsumer.test:
                await self._send("progress", 0)
                for index, combination in enumerate(TestConsumer.combinations, start=1):
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
            if "manuell" in TestConsumer.test:
                await self._send("progress", 0)
                if TestConsumer.index != len(TestConsumer.combinations) + 1:
                    combination = TestConsumer.combinations[TestConsumer.index - 1]
                    print(f'Combination: {TestConsumer.index}: {combination}')
                    await self._send("testnum", TestConsumer.index)
                    for rel in range(len(combination)):
                        if combination[rel] != None:
                            self.modbus.set_relays(combination[rel], 'on')
                            await asyncio.sleep(0.02)
                    await self.send_progress(TestConsumer.index)
                    await asyncio.sleep(0.5)
                    await self.modbus.reset_all()
                    index = 0
            print(index, TestConsumer.index, len(TestConsumer.combinations))
            if index or TestConsumer.index == len(TestConsumer.combinations):
                metadata = dt.now().strftime("%Y_%m_%d-%H_%M_%S")
                filename = (f'{self.path}/TestErgebnis_{metadata}.yaml')
                with open(filename, 'w') as file:
                    file.write(yaml.dump(self.results, indent=4, allow_unicode=True))
                await self.get_metadata()
        except Exception as e:
            show_error(e)
    
    async def check_konfig_file(self):
        """
        Function that strips the by the user uploaded Konfig-File in category- and component-names and passes that information to the 'parser-function' for further analysis.
        Sends the recieved combination-possibilities to the client and passes them to the 'run_combinations-function'.
        """
        try:
            await self._send('Upload erfolgreich')
            with open(f"komp_pruefstand/static/Konfig.txt", "r") as txt:
                lines = txt.readlines()
                breaks = []
                konfig_count = 1
                for index, line in enumerate(lines):
                    l = line.find('\n')
                    if l == 0:
                        breaks.append(index)
                        konfig_count += 1
                if konfig_count == 1:
                    c = await self.parser(lines) # type: ignore
                    TestConsumer.combinations = c or []
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
                        if len(combination) == 1 and combination[0] not in TestConsumer.combinations:
                            TestConsumer.combinations.append(combination[0])
                        else:
                            for c in range(len(combination)):
                                if combination[c] not in TestConsumer.combinations:
                                    TestConsumer.combinations.append(combination[c])
                print(f'\nAnzahl der Kombinationen: {len(TestConsumer.combinations)}')
                await self._send("combinations", TestConsumer.combinations)
                await self._send("konfigquantity", len(TestConsumer.combinations))
                await self.run_combinations()
        except Exception as e:
            show_error(e)
            
    async def parser(self, lines:list[str]):
        """
        Function for parsing the uploaded Config-File from the user. Checks for wrong written category (Motor, Display, etc.) and component-names (e.g. HPR50).
        Takes the individual components from each category and safes them in a list, which compares the given name of the component with the names in the Master-Konfig-File and gives back the individual stored number of the relay.
        
        Returns list of all the possible interconnections from the given Konfig-File.
        
        Parameters:
            lines = list of strings with the individual lines of the Konfig-File.txt
            konfig = dictionary of the loaded Master-Konfig-File in .yaml format
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
                        variants_name[i] = str(self.master[comp][i]['name'])
                        variants_serial[i] = self.master[comp][i]['serial']
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

    def find_names(self, index):
        """
        Matches the choosen relays for one combination with the name of the component variant and saves it into the result dicitonary.
        """
        for relay in TestConsumer.combinations[index-1]:
            for component in self.master:
                for name in self.master[component]:
                    if relay == name['relay']:
                        if name['name'] != None:
                            if name['name'] == 'Ladegerät':
                                del self.results[f'Konfig.{index}']['Komponenten']['Ladegerät/Service Dongle']
                                self.results[f'Konfig.{index}']['Komponenten']['Ladegerät'] = name['serial']
                                break
                            if name['name'] == 'Service Dongle':
                                component = 'Service Dongle'
                                del self.results[f'Konfig.{index}']['Komponenten']['Ladegerät/Service Dongle']
                            self.results[f'Konfig.{index}']['Komponenten'][component] =  name['name']
                            break
                        else:
                            self.results[f'Konfig.{index}']['Komponenten'][component] =  name['serial']
                            break
                if self.results[f'Konfig.{index}']['Komponenten'][component] == '':
                    self.results[f'Konfig.{index}']['Komponenten'][component] = 'Keine Wahl getroffen'
                else:
                    continue
                break
            else:
                continue
            
    async def get_metadata(self):
        """
        Function that creates a dictionary with the filenames of the test results and the metadata (date, time).
        Scans one given test result file for an EMCY-Message and marks it accordingly.
        When complete, the dictionary is send to the server.
        """
        try:
            self.filenames = sorted(glob.glob(self.path + '/*.yaml'))
            self.filenames.reverse()
            metadata = {}
            metadata['TestResult'] = {}
            for i, filename in enumerate(self.filenames):
                print(f'analyzing file {i+1} of {len(self.filenames)}')
                self.results_list[f'{i}'] = {}
                self.results_list[f'{i}']['filename'] = self.filenames[i]
                self.results_list[f'{i}']['created_at'] = os.path.getatime(filename)
                with open(filename, 'r') as file:
                    t = yaml.safe_load(file)
                    if 'EMCY' in t:
                        self.results_list[f'{i}']['emcy'] = True
                    elif not t:
                        os.remove(filename)
                    else:
                        self.results_list[f'{i}']['emcy'] = False
            await self._send("results", self.results_list)
        except Exception as e:
            show_error(e)

    def stop(self):
<<<<<<< HEAD
        self.running = False
=======
        self.running = False
>>>>>>> 7b97fa14591ac76c8a1f80160936462c2f6d9870
