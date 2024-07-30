import itertools
import time
import crcmod
import struct
import crc16 as c16
import yaml
import os
import re
from collections import Counter


test = "auto"

def run_combinations():
    """
    Function that runs through the user selected configurations - according to the choice of 'auto' or 'manual' - and sets the relays of an
    individual combination in the list of all possible combinations. It also sends the current number of the running combination to the client
    for displaying it to the user.
    """
    if test == "auto":
        for index, combination in enumerate(combinations, start=1):
            print(f'Combination {index}: {combination}')
            for rel in range(len(combination)):
                if combination[rel] != None:
                    time.sleep(0.02)
            time.sleep(0.5)
    if test == "manuell_konfig":
        if index != len(combinations) + 1:
            print("break")
            combination = combinations[index - 1]
            print(combinations)
            print(f'Combination: {index}')
            for rel in range(len(combination)):
                if combination[rel] != None:
                    time.sleep(0.02)
            time.sleep(0.5)
            index += 1
        if index == len(combinations) +1:
            print('Alle Kombinatoriken geschalten')
            print("done")
    else:
        print("done")
        
def show_error(exception):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno, exception)

def check_kWh(choices:str):
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
                    #print(f'Index of k: {battery.find("k")}')
                    choice = choice[:k] + ' ' + choice[k:]
                    choices[ind] = choice
    else:
        x = choices[-4:]
        digit = bool(re.search(r'\d', x))
        if not digit:
            if x != ' kWh':
                k = choices.find('k')
                #print(f'Index of k: {choices.find("k")}')
                choices = choices[:k] + ' ' + choices[k:]
    return choices

def parser(lines:list[str], konfig:dict):
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
                choices = check_kWh(choices)
                #choices = list(set(choices))
                #print(Counter(choices).values())
                #choices = check_kWh(choices)
            choices = list(set(choices))
            comp = comp[0]
            for i in range(len(konfig[comp])):
                variants_name[i] = str(konfig[comp][i]['name'])   #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
                variants_serial[i] = konfig[comp][i]['serial']   #Array mit Namen der Unterkomponenten, von Komp, wo Auswahl > 1
            print(f'Anzahl Wahl {comp}: {len(choices)}')
            odds = []
            for name in range(len(choices)):
                z = choices[name].strip()
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
                print("odds")
            f = {'name': [], 'serial': []}
            for index in range(len(konfig[comp])):
                f['name'].append(str(konfig[comp][index]['name']))
                f['serial'].append(konfig[comp][index]['serial'])
            for i in range(len(choices)):
                double_name, double_serial = False, False
                g = choices[i].strip()
                for index in range(len(konfig[comp])):
                    n = str(konfig[comp][index]['name'])
                    s = konfig[comp][index]['serial']
                    nc = f['name'].count(g)
                    sc = f['serial'].count(g)
                    if n == choices[i].strip() and not double_name:
                        j = konfig[comp][index]["relay"]
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
            relays[comp] = set(relay)
        elif comp[1] != 'None':
            #double_serial, double_name = False, False
            if comp[0] == 'Battery' or comp[0] == 'Range EXT':
                comp[1] = check_kWh(comp[1])
            if comp[0] == 'Ladegerät' or comp[0] == 'Service Dongle':
                comp[0] = 'Ladegerät/Service Dongle'
            for name in konfig[comp[0]]:
                print(name)
                if str(name['name']) == comp[1]:
                    r = name['relay']
                if name['serial'] == comp[1]:
                    r = name['relay']
            relays[comp[0]] = [r]
            print(f'{comp[0]} {comp[1]} hat Relay: {r}')
            r = None
            print("----------------------")
    print(f'Relays zu schalten: {relays}\n')
    l = []
    for key in relays:
        if relays[key] != None:
            l.append(relays[key])
        else:
            l.append([None])
    combinations = list(itertools.product(*l))
    return combinations

with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as y:
    with open(f"komp_pruefstand/static/Konfig.txt", "r") as t:
        konfig = yaml.safe_load(y)
        lines = t.readlines()
        breaks = []
        #relays = {}
        combinations = []
        konfig_count = 1
        for index, line in enumerate(lines):
            l = line.find('\n')
            if l == 0:
                breaks.append(index)
                konfig_count += 1
        if konfig_count == 1:
            combinations = parser(lines, konfig)
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
                combination = parser(konfigs[f'Konfig{k+1}'], konfig)
                if len(combination) == 1:
                    combinations.append(combination[0])
                else:
                    for c in range(len(combination)):
                        combinations.append(combination[c])
        print(f'\nAnzahl der Kombinationen: {len(combinations)}\nCombinations{combinations}')
        if test == "auto":
            run_combinations()
            print('Alle Kombinatoriken geschalten')
            print("done")
        if test == "manuell_konfig":
            run_combinations()
            if index == len(combinations) + 1:
                print('Alle Kombinatoriken geschalten')
                print("done")

