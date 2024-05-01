import yaml
import itertools
import time


# konfigs[f'Konfig{1}'] = {}
# konfigs[f'Konfig{1}']['Motor'] = []
# konfigs[f'Konfig{1}']['Motor'].append(1)
# konfigs[f'Konfig{1}']['Motor'].append(2)
# print(konfigs)

combinations = []

def parser(lines, konfig, cons, relays):
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
            comp = comp[0]
            for i in range(len(konfig[comp])):
                variants[i] = konfig[comp][i]['name']   #Array mit Namen der Unterkomponenten, von Komp, wo Aushwahl > 1
            print(f'\nAnzahl Wahl {comp}: {len(choices)}')
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
            for i in range(len(choices)):
                for index in range(len(konfig[comp])):
                    k = konfig[comp][index]['name']
                    if k == choices[i].strip():
                        relay.append((konfig[comp][index]["relay"]))
                        print(f'ff{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
            relay.sort()
            relays[comp] = relay
        elif comp[1] != 'None':
            for motor in range(len(konfig[comp[0]])):
                name = konfig[comp[0]][motor]['name']
                if name == comp[1]:
                    relay = konfig['Motor'][motor]["relay"]
                    #print(f'{comp[1]} hat Relay {relay}')
            relays[comp[0]] = [(konfig[comp[0]][motor]["relay"])]
            print(f'{comp[0]}, {comp[1]} hat Relay: {relay}')
    print(f'Relays zu schalten: {relays}')
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
        cons = list(konfig.keys())
        breaks = []
        comps = {}
        for key in konfig:
            comps[key] = {}
        lines = t.readlines()
        #print(lines)
        relays = {}
        konfig_count = 1
        for index, line in enumerate(lines):
            l = line.find('\n')
            if l == 0:
                breaks.append(index)
                konfig_count += 1
        if konfig_count == 1:
            combinations = parser(lines, konfig, cons, relays)
            print(combinations)
        else:
            print(f'Anzahl Konfigs: {konfig_count}')   
            konfigs = {}
            v = 0
            for k in range(len(breaks)):
                konfigs[f'Konfig{k+1}'] = lines[v:breaks[k]]
                v = breaks[k]+1
                if k+1 == len(breaks):
                    konfigs[f'Konfig{k+2}'] = lines[v:len(lines)]
            print(konfigs['Konfig1'])
            print(konfigs['Konfig2'])
            print(konfigs['Konfig3'])
            for var in konfigs:
                print(var)
                combinations = parser(konfigs[var], konfig, cons, relays)
                #print(breaks[k])
                #konfigs[f'Konfig{k+1}'] = lines[k:breaks[0]]
                    #konfigs[f'Konfig{k+1}'] = lines[breaks[k]:len(lines)]
            #print(konfigs)
            #for h in range(konfig_count):
                #print(lines[a:breaks[h]])
                #a = breaks[h]
            #print(f'{num} in Zeile: ')
            #print(len(breaks))
            #for g in range(konfig_count):

for n in konfig['Motor']:
    print(n['relay'])

# j = 'HPR30'
# for motor in range(len(konfig['Motor'])):
#     name = konfig['Motor'][motor]['name']
#     if name == j:
#         relay = konfig['Motor'][motor]["relay"]
#         print(f'{j} hat Relay {relay}')
# print(konfig['Motor'][0]['relay'])
