#!/usr/bin/env python3
"""
CORRECCIÓN CRÍTICA: Refill Loop Infinito
Ejecutar ANTES de iniciar el bot
"""
import json

print("=" * 60)
print("CORRECCIÓN CRÍTICA - REFILL CONFIGURATION")
print("=" * 60)

with open('file.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

waypoints = data['_default']['1']['config']['ng_cave']['waypoints']['items']

# Identificar waypoints problemáticos
refill_waypoint_idx = None
checker_waypoint_idx = None

for i, wp in enumerate(waypoints):
    if wp['type'] == 'refill' and i == 4:
        refill_waypoint_idx = i
    elif wp['type'] == 'refillChecker' and i == 6:
        checker_waypoint_idx = i

print(f"\n[BEFORE] Waypoint #4 (refill): ignore={waypoints[4]['ignore']}")
print(f"[BEFORE] Waypoint #6 (refillChecker): ignore={waypoints[6]['ignore']}")

# CORRECCIÓN 1: Activar refill normal
waypoints[4]['ignore'] = False
print(f"\n✅ Waypoint #4 (refill): ignore=False (ACTIVADO)")

# CORRECCIÓN 2: Desactivar refillChecker (temporalmente hasta configurar thresholds)
waypoints[6]['ignore'] = True
print(f"✅ Waypoint #6 (refillChecker): ignore=True (DESACTIVADO)")

# CORRECCIÓN 3: Configurar thresholds realistas en el checker (para uso futuro)
if 'options' in waypoints[6]:
    waypoints[6]['options']['minimumAmountOfManaPotions'] = 10
    waypoints[6]['options']['minimumAmountOfHealthPotions'] = 0
    waypoints[6]['options']['minimumAmountOfCap'] = 50
    print(f"✅ RefillChecker thresholds: mana=10, health=0, cap=50")

# Guardar cambios
with open('file.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 60)
print("✅ CORRECCIÓN APLICADA EXITOSAMENTE")
print("=" * 60)
print("\nCambios realizados:")
print("  1. Refill waypoint (#4) ACTIVADO - El bot PUEDE hacer refill")
print("  2. RefillChecker (#6) DESACTIVADO - No interferirá con hunting")
print("  3. Thresholds configurados para reactivación futura")
print("\nAhora el bot puede:")
print("  ✓ Salir del depot")
print("  ✓ Huntear normalmente")
print("  ✓ Hacer refill cuando llegue al waypoint #4")
print("\nNOTA: RefillChecker desactivado - bot hará refill manual cada ciclo")
print("      Para activar checker automático, cambiar waypoint #6 ignore=False")
print("=" * 60)
