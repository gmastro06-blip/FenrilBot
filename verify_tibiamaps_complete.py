"""
Verificación completa de waypoints contra TibiaMaps.io
Descarga markers.json y valida TODOS los scripts en scripts-converted/
"""
import json
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Configuración
BASE_DIR = Path(__file__).parent
SCRIPTS_DIR = BASE_DIR / "scripts-converted"
MARKERS_URL = "https://tibiamaps.github.io/tibia-map-data/markers.json"

def download_markers() -> Dict[Tuple[int, int, int], str]:
    """Descarga markers.json desde TibiaMaps.io"""
    print("📥 Descargando markers.json desde TibiaMaps.io...")
    
    try:
        with urllib.request.urlopen(MARKERS_URL, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        markers = {}
        for marker in data:
            x = marker.get('x')
            y = marker.get('y')
            z = marker.get('z')
            desc = marker.get('description', '')
            icon = marker.get('icon', '')
            
            if x is not None and y is not None and z is not None:
                key = (x, y, z)
                full_desc = f"{desc} ({icon})" if desc else icon
                markers[key] = full_desc
        
        print(f"✅ Descargados {len(markers):,} markers")
        return markers
    
    except Exception as e:
        print(f"❌ Error descargando markers: {e}")
        print("⚠️ Usando conjunto reducido de markers conocidos...")
        return load_fallback_markers()

def load_fallback_markers() -> Dict[Tuple[int, int, int], str]:
    """Markers de respaldo si falla la descarga"""
    markers = {}
    known_coords = [
        (32681, 31687, 6, "Ab'Dendriel depot z6"),
        (32670, 31659, 6, "NPC refill area"),
        (32656, 31674, 7, "Wasp cave"),
    ]
    
    for x, y, z, desc in known_coords:
        markers[(x, y, z)] = desc
    
    return markers

def load_pilotscript(filepath: Path) -> List[Dict]:
    """Carga un archivo .pilotscript (formato JSON)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        waypoints = []
        if isinstance(data, list):
            for i, wp in enumerate(data):
                if isinstance(wp, dict) and 'coordinate' in wp:
                    coord = wp['coordinate']
                    if len(coord) == 3:
                        waypoints.append({
                            'index': i,
                            'coordinate': tuple(coord),
                            'type': wp.get('type', 'unknown'),
                            'label': wp.get('label', ''),
                            'ignore': wp.get('ignore', False)
                        })
        
        return waypoints
    
    except Exception as e:
        return []

def verify_coordinates(waypoint: Tuple[int, int, int], markers: Dict, tolerance: int = 1) -> Tuple[str, str, Optional[Tuple[int, int, int]]]:
    """Verifica si un waypoint existe en TibiaMaps"""
    x, y, z = waypoint
    
    # Coincidencia exacta
    if (x, y, z) in markers:
        return ('MATCH', f'✅ {markers[(x, y, z)]}', (x, y, z))
    
    # Coincidencias cercanas
    closest_coord = None
    closest_distance = float('inf')
    
    for dx in range(-tolerance, tolerance + 1):
        for dy in range(-tolerance, tolerance + 1):
            if dx == 0 and dy == 0:
                continue
            coord = (x + dx, y + dy, z)
            if coord in markers:
                distance = abs(dx) + abs(dy)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_coord = coord
    
    if closest_coord:
        return ('CLOSE', f'🟡 {closest_distance}sqm: {markers[closest_coord]}', closest_coord)
    
    return ('MISSING', '❌ No marker within 1sqm', None)

def generate_report(results: List[Dict], markers: Dict, output_file: str = "WAYPOINTS_VERIFICATION_REPORT.md"):
    """Genera reporte detallado"""
    report_path = BASE_DIR / output_file
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Verificación de Waypoints contra TibiaMaps.io\n\n")
        f.write(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Total markers TibiaMaps**: {len(markers):,}\n\n")
        
        # Resumen global
        total_waypoints = sum(sum(r['stats'].values()) for r in results)
        total_match = sum(r['stats']['match'] for r in results)
        total_close = sum(r['stats']['close'] for r in results)
        total_missing = sum(r['stats']['missing'] for r in results)
        
        f.write("## Resumen Global\n\n")
        f.write(f"- **Total waypoints**: {total_waypoints:,}\n")
        if total_waypoints > 0:
            f.write(f"- ✅ **Match exacto**: {total_match} ({total_match/total_waypoints*100:.1f}%)\n")
            f.write(f"- 🟡 **Cercano (±1 sqm)**: {total_close} ({total_close/total_waypoints*100:.1f}%)\n")
            f.write(f"- ❌ **Sin validar**: {total_missing} ({total_missing/total_waypoints*100:.1f}%)\n\n")
        
        # Resultados por directorio
        f.write("## Resultados por Directorio\n\n")
        
        for result in sorted(results, key=lambda x: x['stats']['missing'], reverse=True):
            stats = result['stats']
            total = sum(stats.values())
            
            if total == 0:
                continue
            
            f.write(f"### 📂 {result['directory']}\n\n")
            f.write(f"- Total: {total} waypoints\n")
            f.write(f"- ✅ Match: {stats['match']} ({stats['match']/total*100:.1f}%)\n")
            f.write(f"- 🟡 Close: {stats['close']} ({stats['close']/total*100:.1f}%)\n")
            f.write(f"- ❌ Missing: {stats['missing']} ({stats['missing']/total*100:.1f}%)\n\n")
            
            # Waypoints críticos con problemas
            critical = [wp for wp in result['waypoints'] 
                       if wp['type'] in ['depositItems', 'refill'] and wp['status'] in ['CLOSE', 'MISSING']]
            
            if critical:
                f.write("#### ⚠️ Waypoints Críticos\n\n")
                f.write("| Tipo | Coordenada | Status |\n")
                f.write("|------|------------|--------|\n")
                for wp in critical:
                    x, y, z = wp['coord']
                    f.write(f"| `{wp['type']}` | [{x}, {y}, {z}] | {wp['status']} |\n")
                f.write("\n")
    
    print(f"\n📄 Reporte guardado: {report_path.name}")

def main():
    print("=" * 80)
    print("VERIFICACIÓN COMPLETA - TIBIAMAPS.IO")
    print("=" * 80)
    print()
    
    # Descargar markers
    markers = download_markers()
    print()
    
    # Obtener directorios
    directories = [d for d in SCRIPTS_DIR.iterdir() if d.is_dir()]
    print(f"📁 Directorios en scripts-converted/: {len(directories)}")
    print()
    
    # Procesar
    total_waypoints = 0
    total_match = 0
    total_close = 0
    total_missing = 0
    results = []
    processed = 0
    
    print("🔍 Procesando...")
    for directory in sorted(directories):
        pilotscripts = list(directory.glob("*.pilotscript"))
        
        if not pilotscripts:
            continue
        
        dir_results = {
            'directory': directory.name,
            'waypoints': [],
            'stats': {'match': 0, 'close': 0, 'missing': 0}
        }
        
        for script in pilotscripts:
            waypoints = load_pilotscript(script)
            
            for wp in waypoints:
                coord = wp['coordinate']
                status, message, closest = verify_coordinates(coord, markers)
                
                total_waypoints += 1
                dir_results['stats'][status.lower()] += 1
                
                if status == 'MATCH':
                    total_match += 1
                elif status == 'CLOSE':
                    total_close += 1
                else:
                    total_missing += 1
                
                dir_results['waypoints'].append({
                    'coord': coord,
                    'type': wp['type'],
                    'label': wp['label'],
                    'status': status,
                    'message': message,
                    'ignore': wp['ignore']
                })
        
        if dir_results['waypoints']:
            results.append(dir_results)
            processed += 1
            
            stats = dir_results['stats']
            total = sum(stats.values())
            print(f"  ✓ {directory.name:35s} {total:4d} wps  [✅{stats['match']:4d} 🟡{stats['close']:4d} ❌{stats['missing']:4d}]")
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN GLOBAL")
    print("=" * 80)
    print(f"📂 Directorios procesados: {processed}/{len(directories)}")
    print(f"📍 Total waypoints: {total_waypoints:,}")
    
    if total_waypoints > 0:
        print(f"✅ Match exacto: {total_match:,} ({total_match/total_waypoints*100:.1f}%)")
        print(f"🟡 Cercano (±1 sqm): {total_close:,} ({total_close/total_waypoints*100:.1f}%)")
        print(f"❌ Sin validar: {total_missing:,} ({total_missing/total_waypoints*100:.1f}%)")
    
    # Generar reporte
    if results:
        generate_report(results, markers)
    
    # Problemas críticos
    critical_issues = [r for r in results 
                      if any(wp['type'] in ['depositItems', 'refill'] and wp['status'] == 'MISSING' 
                            for wp in r['waypoints'])]
    
    if critical_issues:
        print("\n" + "=" * 80)
        print("⚠️ PROBLEMAS CRÍTICOS (depot/refill MISSING)")
        print("=" * 80)
        for issue in critical_issues:
            critical_wps = [wp for wp in issue['waypoints'] 
                           if wp['type'] in ['depositItems', 'refill'] and wp['status'] == 'MISSING']
            print(f"\n📂 {issue['directory']}")
            for wp in critical_wps:
                x, y, z = wp['coord']
                print(f"   ❌ {wp['type']:15s} [{x}, {y}, {z}]")
    
    print("\n" + "=" * 80)
    print("NOTAS")
    print("=" * 80)
    print("✓ Markers descargados desde TibiaMaps.io oficial")
    print("✓ MATCH/CLOSE son confiables para uso")
    print("⚠ MISSING puede ser válido (paths personalizados)")
    print("⚠ Verificar depot/refill MISSING in-game antes de usar")
    print()

if __name__ == "__main__":
    main()
