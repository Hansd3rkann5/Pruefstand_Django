import itertools
import time
import yaml

comb = []
arr = [1, 5, None, 13, 20, 23]
comb.append(arr)
print(type(arr))
print(comb)

# battery = '320kWh'
# print(battery[-4:])

# def parser(lines, konfig, cons, relays):
#     for key in cons:
#         relays[key] = None
#     for line in lines:
#         string = line.rstrip()
#         relay = []
#         comp = [x.strip() for x in string.split(':', line.find(':'))]
#         komma = line.find(",")
#         if comp[0] == 'Range Ext' or comp[0] == 'RangeExt':
#             comp[0] = 'Range EXT'
#         if komma != -1:
#             variants = [''] * len(konfig[comp[0]])
#             choices = [x.strip() for x in comp[1].split(',')]
#             if comp[0] == 'Battery' or comp[0] == 'Range EXT':
#                 choices = check_kWh(choices)
#             comp = comp[0]
#             for i in range(len(konfig[comp])):
#                 variants[i] = konfig[comp][i]['name']   #Array mit Namen der Unterkomponenten, von Komp, wo Aushwahl > 1
#             print(f'Anzahl Wahl {comp}: {len(choices)}')
#             odds = []
#             for name in range(len(choices)):
#                 if choices[name].strip() not in variants:
#                     odds.append((choices[name].strip()))
#             if len(odds) <= 1:
#                 num = 'sind'
#                 num1 = 'ist'
#             else:
#                 num = 'ist'
#                 num1 = 'sind'
#             if len(odds) != 0:
#                 print(f'Davon {num} aber nur {len(choices) - len(odds)} gültig.')
#                 print(f'{comp} {odds} {num1} ungültig')
#                 odds.append(comp)
#             for i in range(len(choices)):
#                 for index in range(len(konfig[comp])):
#                     k = konfig[comp][index]['name']
#                     if k == choices[i].strip():
#                         relay.append((konfig[comp][index]["relay"]))
#                         print(f'{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
#             relay.sort()
#             relays[comp] = relay
#         elif comp[1] != 'None':
#             if comp[0] == 'Battery' or comp[0] == 'Range EXT':
#                 comp[1] = check_kWh(comp[1])
#             for name in konfig[comp[0]]:
#                 if name['name'] == comp[1]:
#                     r = name['relay']
#             relays[comp[0]] = [r]
#             print(f'{comp[0]}, {comp[1]} hat Relay: {r}')
#             r = -1
#     print(f'Relays zu schalten: {relays}\n')
#     l = []
#     for key in relays:
#         if relays[key] != None:
#             l.append(relays[key])
#         else:
#             l.append([None])
#     combinations = list(itertools.product(*l))
#     return combinations

#     def check_kWh(choices):
#         if type(choices) != str:
#             for ind, choice in enumerate(choices):
#                 t = choice[-4:]
#                 if choice[-4:] != ' kWh':
#                     k = choice.find('k')
#                     #print(f'Index of k: {battery.find("k")}')
#                     choice = choice[:k] + ' ' + choice[k:]
#                     choices[ind] = choice
#         else:
#             x = choices[-4:]
#             if choices[-4:] != ' kWh':
#                 k = choices.find('k')
#                 #print(f'Index of k: {choices.find("k")}')
#                 choices = choices[:k] + ' ' + choices[k:]
#         return choices

# with open(f"komp_pruefstand/static/Komponenten.yaml", "r") as y:
#     with open(f"komp_pruefstand/static/Konfig.txt", "r") as t:
#         konfig = yaml.safe_load(y)
#         cons = list(konfig.keys())
#         lines = t.readlines()
#         breaks = []
#         relays = {}
#         combinations = []
#         konfig_count = 1
#         for index, line in enumerate(lines):
#             l = line.find('\n')
#             if l == 0:
#                 breaks.append(index)
#                 konfig_count += 1
#         if konfig_count == 1:
#             combinations = parser(lines, konfig, cons, relays)
#         else:
#             print(f'Anzahl Konfigs: {konfig_count}')
#             konfigs = {}
#             v = 0
#             for k in range(len(breaks)):
#                 konfigs[f'Konfig{k+1}'] = lines[v:breaks[k]]
#                 v = breaks[k]+1
#                 if k+1 == len(breaks):
#                     konfigs[f'Konfig{k+2}'] = lines[v:len(lines)]
#             for k in range(konfig_count):
#                 #print(f'\nKonfig{k+1}: {konfigs[f"Konfig{k+1}"]}')
#                 combination = parser(konfigs[f'Konfig{k+1}'], konfig, cons, relays)
#                 if len(combination) == 1:
#                     combinations.append(combination[0])
#                 else:
#                     for c in range(len(combination)):
#                         combinations.append(combination[c])
#     print(f'\nAnzahl der Kombinationen: {len(combinations)}\n{combinations}')
#     print('Alle Kombinatoriken geschalten')

