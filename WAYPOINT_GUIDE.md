# 🗺️ Guía de Waypoints - FenrilBot

## 📋 Resumen de Problemas Encontrados y Solucionados

### ✅ Problemas Corregidos

1. **KeyError con backpacks Golden/Green/Red** 
   - **Problema**: `ScrollToItemTask` intentaba usar imágenes de slots/ que no existen
   - **Solución**: Modificado `depositItems.py` para hacer las imágenes de slots opcionales
   - **Archivo**: `src/gameplay/core/tasks/depositItems.py`

2. **Validación de backpacks demasiado estricta**
   - **Problema**: Validaba tanto containersBars como slots, pero slots es opcional
   - **Solución**: Solo validar containersBars en el try/except
   - **Archivo**: `src/gameplay/core/tasks/depositItems.py` líneas 47-59

3. **Waypoints duplicados en la misma coordenada**
   - **Problema**: Waypoints #41, #42, #43 en [32681, 31687, 6] causaban loops
   - **Solución**: Auto-fixer marcó waypoint #41 como ignore=true
   - **Archivo**: `file.json`

### ⚠️ Problemas Pendientes (Requieren Atención)

1. **Bot inicia lejos de los waypoints activos**
   - El personaje está en `(32708, 31705, 6)`
   - El waypoint activo más cercano es #11 en `[32656, 31674, 6]` (26 sqm)
   - **Solución**: Marcar algunos waypoints intermedios como `ignore=false` para crear un camino

2. **useRope failures**
   - Mensaje: `[UseRopeWaypoint] FAILED 3 times at [32612, 31683, 10], expected Z=9`
   - **Causa**: El bot está en el piso equivocado o la rope no funciona en esa coordenada
   - **Solución**: Verificar que el personaje esté en el sqm correcto antes de usar rope

## 🛠️ Herramientas Incluidas

### 1. Analizador de Waypoints
```bash
python analyze_waypoints.py
```
**Detecta**:
- Waypoints muy cercanos (< 3 sqm) que pueden causar loops
- Waypoints duplicados en la misma coordenada
- Problemas con depositItems (debe estar cerca de "refill")
- useRope/useLadder con ignore=true
- Waypoints intermedios que deberían ser ignorados

**Modo auto-fix**:
```bash
python analyze_waypoints.py --fix
```
Aplica correcciones automáticas como:
- Marcar waypoints duplicados como ignore=true
- Corregir labels de refill
- Activar waypoints críticos (useRope, depositItems)

### 2. Visualizador de Waypoints
```bash
python visualize_waypoints.py
```
Muestra la ruta completa organizada por pisos y zonas.

**Solo waypoints activos**:
```bash
python visualize_waypoints.py --active-only
```

## 📊 Estado Actual de los Waypoints

**Estadísticas**:
- Total: 44 waypoints
- Activos (ignore=false): 11
- Ignorados (ignore=true): 33

**Waypoints Activos por Tipo**:
- walk: 7
- useRope: 3
- useLadder: 1
- depositItems: 1

**Ruta Activa**:
1. `#01: depositItems @ [32681, 31686, Z=6]` - Refill
2. `#11: walk @ [32656, 31674, Z=6]` - Salir del depot
3. `#16: walk @ [32603, 31704, Z=7]` - Hunt area
4. `#18: walk @ [32616, 31700, Z=8]` - Bajar
5. `#19: walk @ [32612, 31683, Z=9]` - Rope area
6. `#23: useRope @ [32612, 31683, Z=10]` - Subir
7. `#29: useRope @ [32622, 31691, Z=9]` - Subir
8. `#31-33: walk + useRope` - Ruta de regreso
9. `#39: useLadder @ [32656, 31674, Z=7]` - Volver al depot

## 🔧 Configuración de Backpacks

**Configuración Actual**:
- Main: Green Backpack ✅
- Loot: Golden Backpack ✅

**Templates Disponibles**:
- containersBars (requerido): ✅ Ambos existen
- slots (opcional): ❌ No existen para Golden/Green

**Impacto**: 
- ✅ Bot puede abrir y detectar backpacks
- ⚠️ `ScrollToItemTask` se saltará (no afecta funcionalidad crítica)
- ✅ `depositItems` funcionará correctamente

## 🎯 Recomendaciones

### Alta Prioridad

1. **Agregar waypoints intermedios del depot al hunt**
   - El salto de `[32681, 31686, 6]` (depot) a `[32656, 31674, 6]` es de 26 sqm
   - Sugerencia: Agregar 2-3 waypoints intermedios con `ignore=false`
   
2. **Verificar coordenada inicial del bot**
   - Si el bot inicia en `(32708, 31705, 6)`, agregar un waypoint cerca de ahí
   - O mover el personaje al depot antes de iniciar

3. **Revisar useRope failures**
   - Waypoint #23: `[32612, 31683, 10]` falla constantemente
   - Verificar que el personaje esté parado exactamente en ese sqm
   - Considerar ajustar la coordenada ±1 sqm si es necesario

### Media Prioridad

4. **Optimizar waypoints ignorados**
   - Tienes 33 waypoints ignorados de 44 (75%)
   - Considera limpiar los que nunca se usarán
   - Mantén los ignorados solo si planeas reactivarlos

5. **Agregar labels descriptivos**
   - Solo 4 waypoints tienen labels útiles
   - Sugerencia: Agregar labels como "entrance", "stairs", "rope_up", etc.

6. **Configurar `passinho` para áreas estrechas**
   - Ningún waypoint usa `passinho=true`
   - Útil para evitar diagonal walking en dungeons estrechos

### Baja Prioridad

7. **Crear backups de waypoints**
   ```bash
   cp file.json file.json.backup
   ```

8. **Documentar la ruta en comentarios**
   - Agrega notes en el JSON para recordar qué hace cada sección

## 📝 Formato de Waypoint

```json
{
  "label": "hunt",           // Nombre descriptivo (opcional)
  "type": "walk",            // walk, useRope, useLadder, depositItems, etc.
  "coordinate": [32603, 31704, 7],  // [X, Y, Z]
  "options": {},             // Opciones adicionales (action, note, etc.)
  "ignore": false,           // true = saltear, false = ejecutar
  "passinho": false          // true = no diagonal walk
}
```

## 🐛 Debugging Tips

### El bot se queda atascado en un waypoint
```bash
# 1. Ver logs del bot para identificar el waypoint
grep "Waypoint recalibrated" logs/fenril.log

# 2. Analizar waypoints
python analyze_waypoints.py

# 3. Verificar si hay waypoints muy cercanos
# El threshold actual es 10 sqm (ajustable con FENRIL_WAYPOINT_RECALIBRATE_DISTANCE)
```

### El bot oscila entre dos waypoints
```bash
# Síntoma: "Waypoint recalibrated: 41 -> 42" y luego "42 -> 41"
# Causa: Waypoints duplicados o muy cercanos en coordenadas diferentes

# Solución:
python analyze_waypoints.py --fix
```

### depositItems no abre el depot
```bash
# 1. Verificar que los backpacks estén configurados
python visualize_waypoints.py | grep "BACKPACKS"

# 2. Verificar que depositItems tenga ignore=false
python visualize_waypoints.py | grep "depositItems"

# 3. Verificar que el waypoint anterior tenga label "refill"
python analyze_waypoints.py
```

## 🔍 Variables de Entorno Útiles

```bash
# Recalibración de waypoints
FENRIL_WAYPOINT_RECALIBRATE_DISTANCE=10  # Distancia en sqm (default: 10)
FENRIL_WAYPOINT_RECALIBRATE_COOLDOWN_S=30  # Cooldown en segundos (default: 30)

# Logging
FENRIL_LOG_LOOT=true  # Activar logs de loot queue
FENRIL_STATUS_LOG_INTERVAL_S=2.0  # Intervalo de status logs

# Timeouts
FENRIL_SCROLL_TO_ITEM_TIMEOUT=20.0  # Timeout para ScrollToItemTask
```

## 📚 Referencias

- [src/gameplay/core/middlewares/radar.py](src/gameplay/core/middlewares/radar.py) - Lógica de recalibración
- [src/gameplay/core/tasks/depositItems.py](src/gameplay/core/tasks/depositItems.py) - Task de deposit
- [src/gameplay/resolvers.py](src/gameplay/resolvers.py) - Resolución de tasks por tipo de waypoint
- [src/gameplay/core/waypoint.py](src/gameplay/core/waypoint.py) - Funciones de waypoint

## 🆘 Soporte

Si encuentras más problemas:
1. Ejecuta `python analyze_waypoints.py` y copia el output
2. Ejecuta `python visualize_waypoints.py --active-only` 
3. Revisa los logs del bot en la terminal
4. Comparte los 3 outputs para diagnóstico
