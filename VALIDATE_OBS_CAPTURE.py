#!/usr/bin/env python3
"""
VALIDACIÓN OBS CAPTURE
Verifica que el minimap sea visible en la captura
"""
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

print("=" * 80)
print("VALIDACIÓN DE CAPTURA OBS - DIAGNÓSTICO DE MINIMAP")
print("=" * 80)

# Buscar últimos archivos de diagnóstico
debug_dir = Path('debug')
radar_files = sorted(
    debug_dir.glob('dual_diag_radar_match_not_found_*_radar.png'),
    key=lambda x: x.stat().st_mtime,
    reverse=True
)

if not radar_files:
    print("\n❌ No se encontraron archivos de diagnóstico radar")
    print("   Ejecuta el bot primero para generar capturas")
    exit(1)

print(f"\n✅ Encontrados {len(radar_files)} archivos de diagnóstico")
print(f"   Analizando los 5 más recientes...\n")

for i, radar_file in enumerate(radar_files[:5]):
    print(f"[{i+1}/5] {radar_file.name}")
    
    # Cargar imagen
    img = cv2.imread(str(radar_file), cv2.IMREAD_GRAYSCALE)
    
    if img is None:
        print(f"     ❌ No se pudo cargar la imagen")
        continue
    
    h, w = img.shape
    print(f"     Dimensiones: {w}x{h} pixels")
    
    # Análisis de contenido
    mean_intensity = img.mean()
    std_intensity = img.std()
    
    print(f"     Intensidad media: {mean_intensity:.1f}")
    print(f"     Desviación estándar: {std_intensity:.1f}")
    
    # Detección de problemas
    issues = []
    
    if mean_intensity < 5:
        issues.append("⚠️  IMAGEN CASI NEGRA - Minimap no visible")
    elif mean_intensity > 250:
        issues.append("⚠️  IMAGEN CASI BLANCA - Captura incorrecta")
    
    if std_intensity < 5:
        issues.append("⚠️  BAJO CONTRASTE - Minimap puede no ser detectable")
    
    # Verificar si hay contenido estructurado (minimap tiene patrones)
    edges = cv2.Canny(img, 50, 150)
    edge_count = np.count_nonzero(edges)
    edge_percentage = (edge_count / (w * h)) * 100
    
    print(f"     Bordes detectados: {edge_percentage:.2f}%")
    
    if edge_percentage < 1:
        issues.append("⚠️  POCOS BORDES - Posiblemente no hay minimap visible")
    
    if issues:
        print(f"     PROBLEMAS:")
        for issue in issues:
            print(f"       {issue}")
    else:
        print(f"     ✅ Imagen parece contener contenido válido")
    
    print()

print("=" * 80)
print("RECOMENDACIONES:")
print("=" * 80)

print("""
Si ves múltiples imágenes con problemas:

1. VERIFICAR OBS:
   - Abrir OBS Studio
   - Verificar que la fuente "Tibia_Fuente" está capturando el juego
   - Verificar que el minimap es visible en la preview
   - Tools → WebSocket Server Settings → Enable (127.0.0.1:4455)

2. VERIFICAR PROYECTOR:
   - Clic derecho en "Tibia_Fuente" → Proyector de ventana (Fuente)
   - Debe aparecer ventana "Proyector en ventana (Fuente) - Tibia_Fuente"
   - ESTA ventana debe estar abierta mientras el bot corre

3. VERIFICAR TIBIA:
   - El minimap debe estar visible (no minimizado)
   - La ventana de Tibia debe estar en primer plano o el proyector visible
   - Resolución recomendada: 1920x1009

4. SI SIGUE FALLANDO:
   - Incrementar confidence thresholds en src/repositories/radar/core.py
   - Líneas ~70-75: cambiar 0.60 → 0.75, 0.40 → 0.55

Para ver las imágenes manualmente:
   debug/dual_diag_radar_match_not_found_*_radar.png
   (Abre con visor de imágenes para inspección visual)
""")

print("=" * 80)
