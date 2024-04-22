import yaml

cons = ["Motor", "Display", "Battery", "Charger", "Range EXT", "Service Dongle"]
choice = ['Wahl 1', 'Wahl']



with open(f"komp_pruefstand/static/Komponenten/Komponenten.yaml", "r") as y:
    with open(f"komp_pruefstand/static/Komponenten/Konfig.txt", "r") as t:
        konfig = yaml.safe_load(y)
        cons = list(konfig.keys())
        p = t.readlines()
        relays = {}
        for key in cons:
            relays[key] = None
        for line in p:
            string = line.rstrip()
            relay = []
            comp = [x.strip() for x in string.split(':', line.find(':'))]
            komma = line.find(",")
            if comp[0] == 'Range Ext' or comp[0] == 'RangeExt':
                comp[0] = 'Range EXT'
            if komma != -1:
                variants = [''] * len(konfig[comp[0]])
                choices = [x.strip() for x in comp[1].split(',', comp[1].find(','))]
                comp = comp[0]
                for i in range(len(konfig[comp])):
                    variants[i] = konfig[comp][i]['name']   #Array mit Namen der Unterkomponenten, von Komp, wo Aushwahl > 1
                print(f'\nAnzahl Wahl {comp}: {len(choices)}')
                odds = []
                for name in range(len(choices)):
                    if choices[name].strip() not in variants:
                        odds.append((choices[name].strip()))
                if len(odds) > 1:
                    num = 'sind'
                else:
                    num = 'ist'
                print(f'Davon {num} aber nur {len(choices) - len(odds)} gültig.')
                print(f'{comp} {odds} {num} ungültig')
                for i in range(len(choices)):
                    for index in range(len(konfig[comp])):
                        k = konfig[comp][index]['name']
                        if k == choices[i].strip():
                            relay.append((konfig[comp][index]["relay"]))
                            print(f'{comp}, {choices[i]} hat Relay: {konfig[comp][index]["relay"]}')
                relay.sort()
                relays[comp] = relay
            elif comp[1] != 'None':
                relays[comp[0]] = [(konfig[comp[0]][0]["relay"])]
                print(f'{comp[0]}, {comp[1]} hat Relay: {konfig[comp[0]][0]["relay"]}')
        print(f'Relays zu schalten: {relays}')

for key in relays:
    if relays[key] != None:
        if len(relays[key]) != 1:
            print(f'{key} hat mehr als 1')