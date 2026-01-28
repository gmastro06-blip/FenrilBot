import json

with open('file.json') as f:
    d = json.load(f)

wps = d['_default']['1']['config']['ng_cave']['waypoints']['items']

print('Waypoints de Refill:')
for i, w in enumerate(wps):
    if w['type'] in ['refill', 'refillChecker']:
        print(f'  #{i}: {w["type"]:15s} ignore={w.get("ignore")} coord={w["coordinate"]}')
        if w['type'] == 'refillChecker':
            print(f'       Options: {w.get("options", {})}')
