import itertools
from sqlite3 import Timestamp
import time
import crcmod
import struct
import crc16 as c16
import yaml
import os
import re
import pandas as pd
import glob
from datetime import datetime as dt
from collections import Counter
try:
    from .PCAN.libpcanbasic.examples.console.Python.ManualRead.ManualRead import ManualRead
except ImportError:
    from PCAN.libpcanbasic.examples.console.Python.ManualRead.ManualRead import ManualRead

df = pd.DataFrame(pd.read_csv('/home/simonbader/Coding/Fehlerliste.csv', sep=';', dtype=str))
with open(f'/home/simonbader/Coding/TestResults/TestErgebnis_2024_08_24-12_36_17.yaml', 'r') as file:
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
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Fehlerbeschreibung'] = df.loc[(df['CODE'] == str(code)) & (df['GROUP'] == str(group)), 'Fehlerbeschreibung'].values[0]
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Komponentefehlerbezeichnung'] = df.loc[(df['CODE'] == str(code)) & (df['GROUP'] == str(group)), 'Komponentefehlerbezeichnung'].values[0]
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Komponentenfehlernummer'] = df.loc[(df['CODE'] == str(code)), 'Komponentenfehlernummer'].values[0]
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Fehlerkomponente'] = df.loc[(df['COMP'] == str(comp)), 'Fehlerkomponente'].values[0]
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Fehlergruppe'] = df.loc[(df['GROUP'] == str(group)) & (df['CODE'] == str(code)), 'Fehlergruppe'].values[0]
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Schweregrad'] = df.loc[(df['GROUP'] == str(group)) & (df['CODE'] == str(code)), 'Schweregrad'].values[0]
results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Fehlerbeschreibung'] = df.loc[(df['CODE'] == str(code)) & (df['GROUP'] == str(group)), 'Fehlerbeschreibung'].values[0]
# results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Mögliche Fehlerursache'] = df.loc[(df['GROUP'] == str(group)) & (df['CODE'] == str(code)), 'Mögliche Fehlerursache'].values[0]
d = df.loc[(df['GROUP'] == str(group)) & (df['CODE'] == str(code)), 'Mögliche Fehlerursache'].values[0]
if "\n" in d:
    results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY']['Mögliche Fehlerursache'] = d.splitlines()
print(results['Test1']['Prio1']['DISPLAY']['P1_MSG_EMCY'])

with open(f'/home/simonbader/Coding/TestResults/TestErgebnis_2024_08_24-12_36_17.yaml', 'w') as file:
    file.write(yaml.dump(results, indent=4, allow_unicode=True))