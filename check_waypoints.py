import json

with open('file.json') as f:
    d = json.load(f)

wps = d['_default']['1']['config']['ng_cave']['waypoints']['items']

print('Waypoints de Refill/RefillChecker:')
for i, w in enumerate(wps):
    if w['type'] in ['refill', 'refillChecker']:
        label = w.get('label', '')
        print(f'{i:3d}: {w["type"]:15s} ignore={w.get("ignore"):5} coord={w["coordinate"]} label="{label}"')
        if w['type'] == 'refillChecker':
            print(f'     Options: {w.get("options", {})}')
