import itertools
from sqlite3 import Timestamp
import time
import crcmod
import struct
import crc16 as c16
import yaml
import os
import pandas as pd
import re
import glob
from datetime import datetime as dt
from collections import Counter
try:
    from .PCAN.libpcanbasic.examples.console.Python.ManualRead.ManualRead import ManualRead
except ImportError:
    from PCAN.libpcanbasic.examples.console.Python.ManualRead.ManualRead import ManualRead


FEHLERGRUPPEN = {
    'ERG_NOINIT':           {'Hex': '0x0', 'Short': ''},
    'ERG_UNGROUPED':        {'Hex': '0x1', 'Short': 'GEN'},
    'ERG_SOFTWARE':         {'Hex': '0x2', 'Short': 'SW'},
    'ERG_HARDWARE': 	    {'Hex': '0x3', 'Short': 'HW'},
    'ERG_CONNECTION':	    {'Hex': '0x4', 'Short': 'CONN'},
    'ERG_COMMUNICATION':	{'Hex': '0x5', 'Short': 'COMM'},
    'ERG_SENSOR':	        {'Hex': '0x6', 'Short': 'SENS'},
    'ERG_OVERTEMP':	        {'Hex': '0x7', 'Short': 'HOT'},
    'ERG_UNDERTEMP':	    {'Hex': '0x8', 'Short': 'COLD'},
    'ERG_UNDERVOLT':	    {'Hex': '0x9', 'Short': 'UV'},
    'ERG_OVERVOLT':	        {'Hex': '0xa', 'Short': 'OV'},
    'ERG_BUTTON':	        {'Hex': '0xb', 'Short': 'BTN'},
    'ERG_UPDATE':	        {'Hex': '0xc', 'Short': 'UPDT'},
}

FEHLERKOMPONENTEN = {
    'ERG_NOINIT':           {'Hex': '0x0', 'Short': ''},
    'ERC_MOTOR':            {'Hex': '0x1', 'Short': 'DRV'},
    'ERC_DISPLAY':          {'Hex': '0x2', 'Short': 'DISP'},
    'ERC_MAIN_BATTERY': 	{'Hex': '0x3', 'Short': 'BATT'},
    'ERC_RANGE_EXTENDER':	{'Hex': '0x4', 'Short': 'REX'},
    'ERC_SPEEDSENSOR':	    {'Hex': '0x5', 'Short': 'SPD'},
    'ERC_SYSTEM':	        {'Hex': '0x6', 'Short': 'SYS'},
    'ERC_REMOTE':	        {'Hex': '0x7', 'Short': 'REM'},
    'ERC_AX':	            {'Hex': '0x8', 'Short': 'AUX'},
    'ERC_CHARGER':	        {'Hex': '0x9', 'Short': 'CHG'},
    'ERC_APP':	            {'Hex': '0xa', 'Short': 'APP'},
}


df = pd.DataFrame(pd.read_csv('/home/simonbader/Coding/Fehlerliste.csv', sep=';', dtype=str))
with open(f'/home/simonbader/Coding/TestResults/TestErgebnis_2024_08_25-11_24_08.yaml', 'r') as file:
    results = yaml.safe_load(file)
data = (results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['DATA']).replace(" ", "")
f = []
for r in range(2, 18, 2): 
    f.append(data[r-2:r])
    # f.append(int(hex(int(data[r-2:r], 16)),16))
print(f)
code = [f'{f[1]}{f[0]}']
group = hex(int(f[2], 16))
comp = hex(int(f[3], 16))
code = int(hex(int(code[0], 16)),16)
print(code, group, comp)
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['CODE'] = code
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['GROUP'] = group
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['COMP'] = comp
results['Test1']['EMCY'] = {}
results['Test1']['EMCY']['Fehler Reporter'] = 'DISPLAY'
results['Test1']['EMCY']['Level'] = df.loc[(df['CODE'] == str(code)) & (df['GROUP'] == str(group)), 'Level'].values[0]
results['Test1']['EMCY']['Komponentefehlerbezeichnung'] = df.loc[(df['CODE'] == str(code)) & (df['GROUP'] == str(group)), 'Komponentefehlerbezeichnung'].values[0]
results['Test1']['EMCY']['Komponentenfehlernummer'] = df.loc[(df['CODE'] == str(code)), 'Komponentenfehlernummer'].values[0]
for er_comp in FEHLERKOMPONENTEN:
    if FEHLERKOMPONENTEN[er_comp]['Hex'] == comp:
        results['Test1']['EMCY']['Fehlerkomponente'] = FEHLERKOMPONENTEN[er_comp]['Short']
        break
for er_comp in FEHLERGRUPPEN:
    if FEHLERGRUPPEN[er_comp]['Hex'] == group:
        results['Test1']['EMCY']['Fehlergruppe'] = FEHLERGRUPPEN[er_comp]['Short']
        break
results['Test1']['EMCY']['Schweregrad'] = df.loc[(df['GROUP'] == str(group)) & (df['CODE'] == str(code)), 'Schweregrad'].values[0]
results['Test1']['EMCY']['Fehlerbeschreibung'] = df.loc[(df['CODE'] == str(code)) & (df['GROUP'] == str(group)), 'Fehlerbeschreibung'].values[0]
d = df.loc[(df['GROUP'] == str(group)) & (df['CODE'] == str(code)), 'Mögliche Fehlerursache'].values[0]
if "\n" in d:
    results['Test1']['EMCY']['Mögliche Fehlerursache'] = d.splitlines()

with open(f'/home/simonbader/Coding/TestResults/TestErgebnis_2024_08_25-11_24_08.yaml', 'w') as file:
    file.write(yaml.dump(results, indent=4, allow_unicode=True))