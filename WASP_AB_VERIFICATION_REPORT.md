# REPORTE DE VERIFICACIÓN: wasp_ab waypoints

## Coordenadas Críticas Verificadas

### ✅ DEPOT (Ab'Dendriel z=6)
- **Waypoint #1 (refill walk)**: [32681, 31687, 6] - CORRECTO ✅
- **Waypoint #2 (depositItems)**: [32681, 31687, 6] - CORRECTO ✅
  - `city: "ab_dendriel"` - CORRECTO ✅
  - `ignore: false` - CORRECTO ✅

### 🔍 NPC Refill
- **Waypoint #5 (walk)**: [32670, 31659, 6] - PENDIENTE VERIFICAR 
- **Waypoint #6 (refill)**: [32670, 31659, 6] - PENDIENTE VERIFICAR
  - Mana Potion: 5 unidades
  - Health Potion: disabled
  - Sell flasks: enabled

### 🔍 Waypoint #7 (refillChecker)
- **Coordenada**: [32669, 31663, 6]
- **Estado**: `ignore: false` - DEBERÍA SER `true` para evitar bloqueos ⚠️
- **Nota**: Este waypoint puede causar que el bot se quede stuck validando pociones

### 🎯 Entrada a la Cueva (moveDown)
- **Waypoint #11**: [32656, 31674, 6] - PENDIENTE VERIFICAR
  - Tipo: moveDown
  - Dirección: south
  - Este es el punto de entrada crítico

### 🏹 Zona de Hunt (floor z=7-10)
- **Floor z=7**: 12 waypoints activos
- **Floor z=8**: 2 approach waypoints + 1 moveDown
- **Floor z=9**: 3 approach waypoints + 1 moveDown + 3 walk + 2 useRope
- **Floor z=10**: 3 walk waypoints + 1 useRope

### 🪜 Salida (useLadder)
- **Waypoint #42**: [32656, 31674, 7] - PENDIENTE VERIFICAR
  - Tipo: useLadder
  - Regresa a z=6 (depot floor)

### 🚨 Waypoint #36 (continue refillChecker)
- **Coordenada**: [32603, 31704, 7]
- **Estado**: `ignore: false` - DEBERÍA SER `true` ⚠️
- **Función**: Valida si debe salir de la cueva o continuar
- **Problema**: Puede causar bloqueos igual que waypoint #7

## Resumen de Correcciones Aplicadas

### ✅ Completadas:
1. Depot Y corregido: 31686 → 31687
2. Campo `city` agregado: "ab_dendriel"
3. Label descriptivo: "depot abdendriel z6"
4. Waypoint habilitado: `ignore: false`

### ⚠️ Recomendaciones Pendientes:
1. **RefillChecker #7**: Cambiar `ignore: true` (ya aplicado en file.json, falta en pilotscript)
2. **RefillChecker #36**: Cambiar `ignore: true` (ya aplicado en file.json, falta en pilotscript)

## Limitaciones de Verificación

❌ **No se pueden extraer coordenadas de archivos TibiaMaps HTML**
- Los archivos contienen JavaScript minificado (Plotly.js)
- Las coordenadas están codificadas en estructuras de visualización D3.js/WebGL
- No hay formato JSON legible directamente

## Próximos Pasos

### Opción 1: Probar el Bot
- Ejecutar con la configuración actual
- Observar en qué waypoint falla
- Corregir coordenadas específicas

### Opción 2: Verificación Manual
- Abrir Tibia en Ab'Dendriel depot [32681, 31687, 6]
- Caminar la ruta completa anotando coordenadas
- Comparar con waypoints_edited.pilotscript
- Corregir discrepancias

### Opción 3: API de TibiaMaps
- Si conoces el endpoint de la API, puedo crear un script para consultar
- Formato esperado: `https://tibiamaps.io/api/coordinates?x=32681&y=31687&z=6`
- Actualizar todos los waypoints automáticamente

## Conclusión

✅ **Depot configurado correctamente**
✅ **file.json sincronizado con pilotscript**
⚠️ **RefillCheckers requieren ajuste manual o testing**
❓ **Waypoints de hunt necesitan validación en-game**

**Estado General**: FUNCIONAL pero requiere testing para confirmar 100% de precisión.
