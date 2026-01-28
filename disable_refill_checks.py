import json

with open('file.json') as f:
    d = json.load(f)

wps = d['_default']['1']['config']['ng_cave']['waypoints']['items']

# Desactivar ambos refillCheckers
for w in wps:
    if w['type'] == 'refillChecker':
        w['ignore'] = True
        print(f'Desactivado refillChecker en {w["coordinate"]}')

with open('file.json', 'w') as f:
    json.dump(d, f, indent=2)

print('\n✅ RefillCheckers desactivados - El bot ahora puede huntear sin validar pociones')
print('⚠️ IMPORTANTE: Compra pociones manualmente antes de huntear')
