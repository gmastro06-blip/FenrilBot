import json

with open('file.json') as f:
    d = json.load(f)

wps = d['_default']['1']['config']['ng_cave']['waypoints']['items']

# Encontrar el waypoint de depot
for i, w in enumerate(wps):
    if w['type'] == 'depositItems':
        print(f'Depot actual: #{i} coord={w["coordinate"]} city={w.get("options", {}).get("city", "NO CONFIGURADO")}')
        
        # Actualizar a las coordenadas correctas de Ab'Dendriel
        w['coordinate'] = [32681, 31687, 6]
        w['options'] = {'city': 'ab_dendriel'}
        w['label'] = 'depot abdendriel z6'
        
        print(f'Actualizado a: coord=[32681, 31687, 6] city=ab_dendriel')

with open('file.json', 'w') as f:
    json.dump(d, f, indent=2)

print('\n✅ Depot configurado para Ab\'Dendriel [32681, 31687, 6] piso z=6')
