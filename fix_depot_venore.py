import json

with open('file.json') as f:
    d = json.load(f)

wps = d['_default']['1']['config']['ng_cave']['waypoints']['items']
depot = [w for w in wps if w['type'] == 'depositItems'][0]

print(f'Depot actual: {depot["coordinate"]}')
depot['coordinate'] = [32681, 31686, 6]
depot['options'] = {'city': 'venore'}
depot['label'] = 'depot venore'
depot['ignore'] = False

with open('file.json', 'w') as f:
    json.dump(d, f, indent=2)

print('✅ Depot configurado para Venore [32681,31686,6]')
