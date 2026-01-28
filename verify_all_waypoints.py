"""
Verifica todos los waypoints de scripts-converted contra archivos TibiaMaps HTML.
Compara las coordenadas en pilotscripts con las coordenadas extraídas de TibiaMaps.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import re

# Directorio base
BASE_DIR = Path(__file__).parent / "scripts-converted"

def extract_coordinates_from_html(html_file: Path) -> set[tuple[int, int, int]]:
    """
    Extrae coordenadas de archivos HTML de TibiaMaps.
    Busca patrones como [x, y, z] en el contenido.
    """
    coords = set()
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Buscar patrones de coordenadas [x, y, z]
        # TibiaMaps usa arrays de JavaScript con coordenadas
        patterns = [
            r'\[(\d+),\s*(\d+),\s*(\d+)\]',  # [x, y, z]
            r'x:\s*(\d+),\s*y:\s*(\d+),\s*z:\s*(\d+)',  # x: 123, y: 456, z: 7
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                x, y, z = int(match.group(1)), int(match.group(2)), int(match.group(3))
                # Filtrar coordenadas que son claramente de Tibia (rango 31000-33000)
                if 31000 <= x <= 33500 and 31000 <= y <= 33000 and 0 <= z <= 15:
                    coords.add((x, y, z))
    
    except Exception as e:
        print(f"  ⚠️  Error leyendo {html_file.name}: {e}")
    
    return coords

def extract_waypoints_from_pilotscript(pilotscript_file: Path) -> list[dict]:
    """Extrae waypoints de un archivo .pilotscript"""
    try:
        with open(pilotscript_file, 'r', encoding='utf-8') as f:
            waypoints = json.load(f)
        return waypoints if isinstance(waypoints, list) else []
    except Exception as e:
        print(f"  ⚠️  Error leyendo {pilotscript_file.name}: {e}")
        return []

def get_floor_from_filename(filename: str) -> int | None:
    """Extrae el número de floor de nombre como waypoints_z6_tibiamaps.html"""
    match = re.search(r'z(\d+)', filename)
    return int(match.group(1)) if match else None

def verify_directory(dir_path: Path) -> dict:
    """Verifica todos los waypoints en un directorio contra TibiaMaps"""
    
    # Buscar archivos
    pilotscripts = list(dir_path.glob("*.pilotscript"))
    html_files = list(dir_path.glob("*tibiamaps*.html"))
    
    if not pilotscripts:
        return None
    
    result = {
        "directory": dir_path.name,
        "pilotscripts": len(pilotscripts),
        "html_files": len(html_files),
        "issues": [],
        "stats": {}
    }
    
    # Si no hay archivos HTML, no podemos verificar
    if not html_files:
        result["issues"].append("⚠️  No se encontraron archivos TibiaMaps HTML para verificación")
        return result
    
    # Extraer coordenadas de TibiaMaps por floor
    tibiamaps_coords_by_floor = defaultdict(set)
    for html_file in html_files:
        floor = get_floor_from_filename(html_file.name)
        if floor is not None:
            coords = extract_coordinates_from_html(html_file)
            tibiamaps_coords_by_floor[floor].update(coords)
            
    # Si no se extrajeron coordenadas, reportar
    total_tibiamaps_coords = sum(len(coords) for coords in tibiamaps_coords_by_floor.values())
    if total_tibiamaps_coords == 0:
        result["issues"].append("⚠️  No se pudieron extraer coordenadas de archivos TibiaMaps HTML")
        return result
    
    # Verificar cada pilotscript
    for pilotscript in pilotscripts:
        waypoints = extract_waypoints_from_pilotscript(pilotscript)
        
        waypoints_checked = 0
        waypoints_matched = 0
        waypoints_unmatched = 0
        critical_issues = []
        
        for i, wp in enumerate(waypoints):
            if not isinstance(wp, dict) or 'coordinate' not in wp:
                continue
                
            coord = wp.get('coordinate', [])
            if len(coord) != 3:
                continue
            
            x, y, z = coord[0], coord[1], coord[2]
            wp_type = wp.get('type', 'unknown')
            wp_label = wp.get('label', '')
            ignore = wp.get('ignore', False)
            
            # Solo verificar waypoints activos (ignore=false)
            if ignore:
                continue
            
            waypoints_checked += 1
            
            # Buscar coordenada exacta en TibiaMaps del mismo floor
            if z in tibiamaps_coords_by_floor:
                if (x, y, z) in tibiamaps_coords_by_floor[z]:
                    waypoints_matched += 1
                else:
                    # Buscar coordenadas cercanas (±1 sqm)
                    nearby_found = False
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if (x + dx, y + dy, z) in tibiamaps_coords_by_floor[z]:
                                nearby_found = True
                                break
                        if nearby_found:
                            break
                    
                    if nearby_found:
                        waypoints_matched += 1
                        result["issues"].append(
                            f"  📍 {pilotscript.name} waypoint #{i} ({wp_type}): "
                            f"Coordenada cercana pero no exacta [{x}, {y}, {z}]"
                        )
                    else:
                        waypoints_unmatched += 1
                        issue_msg = (
                            f"  ❌ {pilotscript.name} waypoint #{i} ({wp_type}): "
                            f"[{x}, {y}, {z}] NO encontrada en TibiaMaps"
                        )
                        if wp_label:
                            issue_msg += f" (label: '{wp_label}')"
                        
                        # Crítico si es depositItems o refill
                        if wp_type in ['depositItems', 'refill']:
                            critical_issues.append(issue_msg + " 🚨 CRÍTICO")
                        else:
                            result["issues"].append(issue_msg)
            else:
                waypoints_unmatched += 1
                result["issues"].append(
                    f"  ⚠️  {pilotscript.name} waypoint #{i} ({wp_type}): "
                    f"Floor z={z} no tiene datos de TibiaMaps"
                )
        
        # Agregar issues críticos al principio
        result["issues"] = critical_issues + result["issues"]
        
        result["stats"][pilotscript.name] = {
            "total": len(waypoints),
            "active": waypoints_checked,
            "matched": waypoints_matched,
            "unmatched": waypoints_unmatched,
            "match_rate": f"{(waypoints_matched / waypoints_checked * 100):.1f}%" if waypoints_checked > 0 else "0%"
        }
    
    return result

def main():
    print("🔍 VERIFICACIÓN DE WAYPOINTS CONTRA TIBIAMAPS")
    print("=" * 80)
    print()
    
    # Obtener todos los subdirectorios
    subdirs = sorted([d for d in BASE_DIR.iterdir() if d.is_dir()])
    
    total_dirs = 0
    dirs_with_issues = 0
    critical_dirs = []
    
    all_results = []
    
    for subdir in subdirs:
        result = verify_directory(subdir)
        
        if result is None:
            continue
        
        total_dirs += 1
        all_results.append(result)
        
        # Determinar si hay problemas
        has_issues = len(result["issues"]) > 0
        has_critical = any("🚨 CRÍTICO" in issue for issue in result["issues"])
        
        if has_issues:
            dirs_with_issues += 1
        
        if has_critical:
            critical_dirs.append(result["directory"])
        
        # Mostrar resultado
        status = "🚨 CRÍTICO" if has_critical else ("⚠️  PROBLEMAS" if has_issues else "✅ OK")
        print(f"{status} {result['directory']}")
        print(f"  📁 {result['pilotscripts']} pilotscript(s), {result['html_files']} HTML TibiaMaps")
        
        # Mostrar estadísticas
        for pilotscript, stats in result["stats"].items():
            print(f"  📊 {pilotscript}: {stats['matched']}/{stats['active']} coinciden ({stats['match_rate']})")
        
        # Mostrar issues
        if result["issues"]:
            for issue in result["issues"][:5]:  # Mostrar máximo 5 issues por directorio
                print(issue)
            if len(result["issues"]) > 5:
                print(f"  ... y {len(result['issues']) - 5} issues más")
        
        print()
    
    # Resumen final
    print("=" * 80)
    print("📊 RESUMEN GENERAL")
    print(f"  Total de directorios verificados: {total_dirs}")
    print(f"  Directorios con problemas: {dirs_with_issues}")
    print(f"  Directorios con problemas CRÍTICOS: {len(critical_dirs)}")
    
    if critical_dirs:
        print(f"\n🚨 DIRECTORIOS CON PROBLEMAS CRÍTICOS:")
        for dir_name in critical_dirs:
            print(f"  - {dir_name}")
    
    # Guardar reporte completo
    report_path = Path(__file__).parent / "waypoint_verification_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Reporte completo guardado en: {report_path}")

if __name__ == "__main__":
    main()
