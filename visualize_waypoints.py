#!/usr/bin/env python3
"""
Waypoint Visualizer
===================
Crea un resumen visual de la ruta de waypoints para entender el flujo del bot.

Uso:
    python visualize_waypoints.py
    python visualize_waypoints.py --active-only  # Solo waypoints activos
"""

import json
import sys
from typing import List, Dict

def load_config(filepath: str = 'file.json') -> Dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['_default']['1']['config']

def get_waypoint_summary(wp: Dict, index: int) -> str:
    """Genera un resumen de un waypoint."""
    coord = wp['coordinate']
    wp_type = wp['type']
    ignore = wp['ignore']
    label = wp.get('label', '')
    passinho = wp.get('passinho', False)
    
    status = "⏭️ " if ignore else "✅"
    label_str = f" '{label}'" if label else ""
    passinho_str = " [PASSINHO]" if passinho else ""
    
    return f"{status} #{index:02d}: {wp_type:15s} @ [{coord[0]}, {coord[1]}, Z={coord[2]}]{label_str}{passinho_str}"

def visualize_route(config: Dict, active_only: bool = False) -> None:
    """Visualiza la ruta completa de waypoints."""
    waypoints = config['ng_cave']['waypoints']['items']
    
    print("\n" + "="*100)
    print("RUTA DE WAYPOINTS - FenrilBot")
    print("="*100)
    
    # Agrupar por zonas (basado en labels y floors)
    current_floor = None
    current_zone = None
    
    for i, wp in enumerate(waypoints):
        if active_only and wp['ignore']:
            continue
        
        coord = wp['coordinate']
        floor = coord[2]
        label = wp.get('label', '')
        
        # Cambio de piso
        if floor != current_floor:
            if current_floor is not None:
                print()
            print(f"\n{'─'*100}")
            print(f"  PISO {floor}")
            print(f"{'─'*100}")
            current_floor = floor
        
        # Cambio de zona importante
        if label and label != current_zone:
            print(f"\n  📍 {label.upper()}")
            current_zone = label
        
        # Imprimir waypoint
        summary = get_waypoint_summary(wp, i)
        print(f"  {summary}")
    
    print("\n" + "="*100)
    
    # Estadísticas
    total = len(waypoints)
    active = sum(1 for w in waypoints if not w['ignore'])
    by_type: Dict[str, int] = {}
    for wp in waypoints:
        if active_only and wp['ignore']:
            continue
        wp_type = wp['type']
        by_type[wp_type] = by_type.get(wp_type, 0) + 1
    
    print("\n📊 ESTADÍSTICAS:")
    print(f"  • Total waypoints: {total}")
    print(f"  • Activos (ignore=false): {active}")
    print(f"  • Ignorados (ignore=true): {total - active}")
    print(f"\n  Tipos de waypoints:")
    for wp_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    - {wp_type:15s}: {count}")
    
    # Backpack config
    backpacks = config.get('ng_backpacks', {})
    print(f"\n🎒 BACKPACKS:")
    print(f"  • Main: {backpacks.get('main', 'No configurado')}")
    print(f"  • Loot: {backpacks.get('loot', 'No configurado')}")
    
    # Runtime settings
    runtime = config.get('ng_runtime', {})
    print(f"\n⚙️  CONFIGURACIÓN:")
    print(f"  • Attack from battlelist: {runtime.get('attack_from_battlelist', False)}")
    print(f"  • Loot modifier: {runtime.get('loot_modifier', 'shift')}")
    print(f"  • Start paused: {runtime.get('start_paused', True)}")
    
    print("\n" + "="*100)

def main() -> None:
    active_only = '--active-only' in sys.argv
    
    if '-h' in sys.argv or '--help' in sys.argv:
        print(__doc__)
        return
    
    print("Cargando configuración...")
    config = load_config()
    visualize_route(config, active_only)
    
    if not active_only:
        print("\n💡 TIP: Usa --active-only para ver solo los waypoints activos (ignore=false)")

if __name__ == '__main__':
    main()
