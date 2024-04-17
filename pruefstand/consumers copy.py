import yaml

cons = ["Motor", "Display", "Battery", "Charger", "Range Ext", "Service Dongle"]

with open(f"komp_pruefstand/static/Komponenten/Konfig.txt", "r") as konfig:
    lines = konfig.readlines()
    for name in cons:
        for line in lines:
            if line.find(name) != -1:
                print(f"{name} : {lines[lines.index(line)][3:]}")