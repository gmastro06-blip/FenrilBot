import json

with open('file.json') as f:
    wps = json.load(f)['_default']['1']['config']['ng_cave']['waypoints']['items']

print('Waypoints ACTIVOS (ignore=False):\n')
for i, w in enumerate(wps):
    if not w.get('ignore', False):
        coord = w['coordinate']
        label = w.get('label', '')
        wtype = w['type']
        print(f'#{i:2d}: {wtype:15s} coord={coord} label="{label}"')
