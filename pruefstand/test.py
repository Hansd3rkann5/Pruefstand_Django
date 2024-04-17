# file = open("komp_pruefstand/static/Komponenten/Motoren.txt", "r")
# data = file.read().splitlines()
# mot = [None] * len(data)
# for i in range(len(data)):
#     mot[i] = data[i]

#mot = [0x00, 0x01, 0x02, 0x03, 0x04]
# disp = [0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C]
# bat = [0x0D, 0x0E, 0x0F, 0x10, 0x12]
# charg = [0x13, 0x14, 0x15]
# ext = [0x16, 0x17, 0x18, 0x19]
# sd = [0x1A, 0x1B]
cons = [
    "Motor", 
    "Display",
    "Battery",
    "Charger",
    "RangeExtender",
    "ServiceDongle"]
comps = {}
#print(cons)

for type in cons:
    file = open(f"komp_pruefstand/static/Komponenten/{type}.txt", "r")
    data = file.read().splitlines()
    comps[type] = data
    print(f"{type}: {len(data)}")
    #print(f"{value}: {data}")
    
#print(comps[cons[1]][1])
    