#!/usr/bin/env python3
"""
Waypoint Analyzer and Fixer
============================
Analiza los waypoints del archivo file.json y detecta problemas comunes:
- Waypoints muy cercanos entre sí que causan loops
- Waypoints en la misma coordenada con diferentes tipos
- Secuencias problemáticas (refill -> hunt sin completar refill)
- Waypoints ignore=false que deberían ser ignore=true

Uso:
    python analyze_waypoints.py                 # Analizar sin cambios
    python analyze_waypoints.py --fix           # Analizar y corregir automáticamente
    python analyze_waypoints.py --interactive   # Modo interactivo para revisar cada cambio
"""

import json
import math
import sys
from typing import List, Dict, Tuple, Any

def load_waypoints(filepath: str = 'file.json') -> Tuple[Dict, List]:
    """Carga los waypoints del archivo JSON."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    config = data['_default']['1']['config']
    waypoints = config['ng_cave']['waypoints']['items']
    return config, waypoints

def save_waypoints(config: Dict, filepath: str = 'file.json') -> None:
    """Guarda los waypoints al archivo JSON."""
    data = {'_default': {'1': {'enabled': True, 'config': config}}}
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ Cambios guardados en {filepath}")

def calculate_distance(coord1: List[int], coord2: List[int]) -> float:
    """Calcula la distancia euclidiana entre dos coordenadas."""
    if coord1[2] != coord2[2]:  # Different floors
        return 999.0
    dx = coord1[0] - coord2[0]
    dy = coord1[1] - coord2[1]
    return math.hypot(dx, dy)

def analyze_waypoints(waypoints: List[Dict]) -> Dict[str, Any]:
    """Analiza los waypoints y retorna problemas detectados."""
    issues = {
        'too_close': [],
        'same_coord': [],
        'depositItems_issues': [],
        'ignore_suggestions': [],
        'useRope_issues': [],
        'total_waypoints': len(waypoints),
        'active_waypoints': sum(1 for w in waypoints if not w['ignore'])
    }
    
    for i, wp in enumerate(waypoints):
        coord = wp['coordinate']
        wp_type = wp['type']
        ignore = wp['ignore']
        label = wp.get('label', '')
        
        # Check for waypoints too close together (< 3 sqm)
        if i < len(waypoints) - 1:
            next_wp = waypoints[i + 1]
            if not next_wp['ignore']:  # Solo considerar waypoints activos
                dist = calculate_distance(coord, next_wp['coordinate'])
                if dist < 3.0 and coord[2] == next_wp['coordinate'][2]:
                    issues['too_close'].append({
                        'index': i,
                        'next_index': i + 1,
                        'distance': dist,
                        'wp1': f"{label or wp_type} @ {coord}",
                        'wp2': f"{next_wp.get('label', '') or next_wp['type']} @ {next_wp['coordinate']}"
                    })
        
        # Check for waypoints at exact same coordinate
        for j in range(i + 1, len(waypoints)):
            if coord == waypoints[j]['coordinate']:
                issues['same_coord'].append({
                    'indices': [i, j],
                    'coordinate': coord,
                    'types': [wp_type, waypoints[j]['type']],
                    'ignores': [ignore, waypoints[j]['ignore']]
                })
        
        # Check depositItems waypoints
        if wp_type == 'depositItems':
            # Should always be at refill location (depot/bank)
            # Check if previous waypoint has 'refill' label
            prev_has_refill = i > 0 and waypoints[i-1].get('label', '').startswith('refill')
            if not prev_has_refill and not label.startswith('refill'):
                issues['depositItems_issues'].append({
                    'index': i,
                    'issue': 'depositItems no está cerca de un waypoint "refill"',
                    'coordinate': coord,
                    'prev_index': i-1 if i > 0 else None
                })
            # Should not be ignored
            if ignore:
                issues['depositItems_issues'].append({
                    'index': i,
                    'issue': 'depositItems está marcado como ignore=true',
                    'coordinate': coord,
                    'prev_index': None
                })
        
        # Check useRope waypoints
        if wp_type == 'useRope':
            # Should never be ignored
            if ignore:
                issues['useRope_issues'].append({
                    'index': i,
                    'issue': 'useRope está marcado como ignore=true',
                    'coordinate': coord
                })
        
        # Suggest ignore for intermediate walk waypoints
        if wp_type == 'walk' and not ignore and not label:
            # If this is between two labeled/important waypoints, suggest ignore=true
            has_prev_label = i > 0 and (waypoints[i-1].get('label') or waypoints[i-1]['type'] != 'walk')
            has_next_label = i < len(waypoints)-1 and (waypoints[i+1].get('label') or waypoints[i+1]['type'] != 'walk')
            if has_prev_label and has_next_label:
                issues['ignore_suggestions'].append({
                    'index': i,
                    'coordinate': coord,
                    'reason': 'waypoint intermedio entre puntos importantes'
                })
    
    return issues

def print_analysis(issues: Dict[str, Any]) -> None:
    """Imprime el análisis de problemas."""
    print("\n" + "="*80)
    print("ANÁLISIS DE WAYPOINTS")
    print("="*80)
    print(f"\n📊 Total waypoints: {issues['total_waypoints']}")
    print(f"✅ Waypoints activos (ignore=false): {issues['active_waypoints']}")
    print(f"⏭️  Waypoints ignorados (ignore=true): {issues['total_waypoints'] - issues['active_waypoints']}")
    
    if issues['too_close']:
        print(f"\n⚠️  WAYPOINTS MUY CERCANOS (< 3 sqm): {len(issues['too_close'])}")
        print("-" * 80)
        for issue in issues['too_close']:
            print(f"  #{issue['index']} y #{issue['next_index']} están a {issue['distance']:.1f} sqm")
            print(f"    • {issue['wp1']}")
            print(f"    • {issue['wp2']}")
    
    if issues['same_coord']:
        print(f"\n🔄 WAYPOINTS EN LA MISMA COORDENADA: {len(issues['same_coord'])}")
        print("-" * 80)
        for issue in issues['same_coord']:
            print(f"  #{issue['indices'][0]} y #{issue['indices'][1]} @ {issue['coordinate']}")
            print(f"    • Tipos: {issue['types'][0]} (ignore={issue['ignores'][0]}), {issue['types'][1]} (ignore={issue['ignores'][1]})")
    
    if issues['depositItems_issues']:
        print(f"\n🏦 PROBLEMAS CON DEPOSITEMS: {len(issues['depositItems_issues'])}")
        print("-" * 80)
        for issue in issues['depositItems_issues']:
            print(f"  #{issue['index']}: {issue['issue']}")
            print(f"    Coordenada: {issue['coordinate']}")
    
    if issues['useRope_issues']:
        print(f"\n🪢 PROBLEMAS CON USEROPE: {len(issues['useRope_issues'])}")
        print("-" * 80)
        for issue in issues['useRope_issues']:
            print(f"  #{issue['index']}: {issue['issue']}")
            print(f"    Coordenada: {issue['coordinate']}")
    
    if issues['ignore_suggestions']:
        print(f"\n💡 SUGERENCIAS DE IGNORE=TRUE: {len(issues['ignore_suggestions'])}")
        print("-" * 80)
        for issue in issues['ignore_suggestions']:
            print(f"  #{issue['index']} @ {issue['coordinate']}")
            print(f"    Razón: {issue['reason']}")
    
    if not any([issues['too_close'], issues['same_coord'], issues['depositItems_issues'], 
                issues['useRope_issues'], issues['ignore_suggestions']]):
        print("\n✅ ¡No se encontraron problemas! Los waypoints parecen estar bien configurados.")

def auto_fix(waypoints: List[Dict], issues: Dict[str, Any]) -> Tuple[List[Dict], int, List[str]]:
    """Aplica correcciones automáticas a los waypoints."""
    fixed: List[str] = []
    changes = 0
    
    # Fix 1: Mark intermediate walk waypoints as ignore=true
    for suggestion in issues['ignore_suggestions']:
        idx = suggestion['index']
        if idx < len(waypoints) and waypoints[idx]['type'] == 'walk' and not waypoints[idx]['ignore']:
            waypoints[idx]['ignore'] = True
            changes += 1
            fixed.append(f"Waypoint #{idx}: ignore=true (intermedio)")
    
    # Fix 2: Ensure depositItems waypoints are not ignored + fix refill label
    for issue in issues['depositItems_issues']:
        idx = issue['index']
        if idx >= len(waypoints):
            continue
        
        if 'ignore=true' in issue['issue']:
            waypoints[idx]['ignore'] = False
            changes += 1
            fixed.append(f"Waypoint #{idx}: ignore=false (depositItems debe ser activo)")
        
        # Fix refill label on previous waypoint
        if issue.get('prev_index') is not None and 'no está cerca' in issue['issue']:
            prev_idx = issue['prev_index']
            if prev_idx >= 0 and prev_idx < len(waypoints):
                if not waypoints[prev_idx].get('label', '').startswith('refill'):
                    waypoints[prev_idx]['label'] = 'refill'
                    changes += 1
                    fixed.append(f"Waypoint #{prev_idx}: label='refill' (antes de depositItems)")
    
    # Fix 3: Ensure useRope waypoints are not ignored
    for issue in issues['useRope_issues']:
        idx = issue['index']
        if idx < len(waypoints):
            waypoints[idx]['ignore'] = False
            changes += 1
            fixed.append(f"Waypoint #{idx}: ignore=false (useRope debe ser activo)")
    
    # Fix 4: For waypoints too close on the same coordinate, set one to ignore=true
    # Prioritize keeping labeled waypoints and action waypoints (depositItems, useRope, etc.)
    processed_coords = set()
    for issue in issues['same_coord']:
        coord_tuple = tuple(issue['coordinate'])
        if coord_tuple in processed_coords:
            continue
        
        indices = issue['indices']
        types = issue['types']
        
        # Keep the first action waypoint, ignore duplicate walks
        if 'walk' in types:
            walk_idx = indices[types.index('walk')]
            other_idx = indices[1 - types.index('walk')]
            
            if waypoints[walk_idx]['type'] == 'walk' and not waypoints[walk_idx].get('label'):
                waypoints[walk_idx]['ignore'] = True
                changes += 1
                fixed.append(f"Waypoint #{walk_idx}: ignore=true (duplicado en {issue['coordinate']})")
        
        processed_coords.add(coord_tuple)
    
    return waypoints, changes, fixed

def main() -> None:
    """Función principal."""
    mode = 'analyze'  # 'analyze', 'fix', 'interactive'
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--fix':
            mode = 'fix'
        elif sys.argv[1] == '--interactive':
            mode = 'interactive'
        elif sys.argv[1] in ['-h', '--help']:
            print(__doc__)
            return
    
    print("Cargando waypoints...")
    config, waypoints = load_waypoints()
    
    print(f"✅ Cargados {len(waypoints)} waypoints")
    
    issues = analyze_waypoints(waypoints)
    print_analysis(issues)
    
    if mode == 'fix':
        print("\n" + "="*80)
        print("APLICANDO CORRECCIONES AUTOMÁTICAS")
        print("="*80)
        waypoints_fixed, changes, fixed_list = auto_fix(waypoints, issues)
        
        if changes > 0:
            print(f"\n✅ {changes} cambios aplicados:")
            for fix in fixed_list:
                print(f"  • {fix}")
            
            config['ng_cave']['waypoints']['items'] = waypoints_fixed
            save_waypoints(config)
        else:
            print("\n✅ No hay cambios que aplicar.")
    
    elif mode == 'interactive':
        print("\n" + "="*80)
        print("MODO INTERACTIVO")
        print("="*80)
        print("(No implementado aún. Use --fix para correcciones automáticas)")
    
    else:
        print("\n" + "="*80)
        print("Para aplicar correcciones automáticas, ejecuta:")
        print("  python analyze_waypoints.py --fix")
        print("="*80)

if __name__ == '__main__':
    main()
