# GUÍA DE TROUBLESHOOTING - FENRILBOT

## ESTADO DEL SISTEMA (28 Enero 2026)

✅ **Funcional**:
- INSERT toggle (activa/pausa bot)
- Headless mode (corre sin GUI)
- Keyboard input (WASD, F1-F12)
- Depot exit configurado
- OBS capture con retry/cache

⚠️ **Experimental** (implementado, no probado):
- Persistent coordinate tracking
- Progress validation
- Auto-recalculation on stuck

❌ **Corregido** (requiere ejecutar FIX_CRITICAL_REFILL.py):
- Refill loop infinito → SOLUCIONADO con script

⚠️ **Riesgo Alto**:
- Radar match failures frecuentes (OBS capture)

---

## PROCEDIMIENTO DE INICIO CORRECTO

### 1. ANTES DE INICIAR EL BOT

```powershell
# Paso 1: Aplicar corrección crítica de refill
python FIX_CRITICAL_REFILL.py

# Paso 2: Validar captura OBS
python VALIDATE_OBS_CAPTURE.py
```

### 2. CONFIGURAR OBS

1. **Abrir OBS Studio**
2. **Verificar fuente "Tibia_Fuente"**:
   - Debe estar capturando la ventana de Tibia
   - Preview debe mostrar el juego con minimap visible
3. **Habilitar WebSocket Server**:
   - Tools → WebSocket Server Settings
   - ✅ Enable WebSocket server
   - Server Port: 4455
   - ❌ Enable Authentication (desactivado)
4. **Abrir Proyector**:
   - Clic derecho en fuente "Tibia_Fuente"
   - → Proyector de ventana (Fuente)
   - Debe aparecer ventana: "Proyector en ventana (Fuente) - Tibia_Fuente"
   - **IMPORTANTE**: Esta ventana debe permanecer abierta

### 3. CONFIGURAR TIBIA

1. Minimap VISIBLE (no minimizado)
2. Personaje en depot o cerca de waypoint #1
3. Inventario abierto (backpacks visibles)
4. Suficientes pociones para al menos 1 ciclo
5. Chat en "local chat" o "default"

### 4. INICIAR BOT

```powershell
python run_bot_persistent.py
```

**Logs esperados**:
```
[run_bot_persistent] Bot threads started. Press ESC to stop.
[run_bot_persistent] Bot running without GUI (headless mode)
[run_bot_persistent] Press INSERT to toggle pause/play
[HH:MM:SS][fenril][info] Paused (ng_pause=1)
```

### 5. ACTIVAR BOT

- Presionar **INSERT** (teclado numérico)
- Log debe mostrar: `INSERT pressed - Bot PLAYING`

### 6. MONITOREAR PRIMEROS 60 SEGUNDOS

**Signos de éxito**:
- `coord=(X, Y, Z)` aparece en logs (coordenadas detectadas)
- `Waypoint recalibrated` aparece (navegación activa)
- `task=walkToWaypoint` o similar (ejecutando tareas)
- Personaje se mueve en Tibia

**Signos de problema**:
- `coord=None` persistente (radar no detecta posición)
- `[fenril][dual] Diagnostics: radar match not found` (captura OBS fallando)
- `Tick reason changed: radar match not found` (sin coordenadas)
- Refill loops (no debería pasar si ejecutaste FIX_CRITICAL_REFILL.py)

---

## PROBLEMAS COMUNES Y SOLUCIONES

### ❌ PROBLEMA: "coord=None" persistente

**Causa**: Radar no puede matchear minimap

**Diagnóstico**:
```powershell
python VALIDATE_OBS_CAPTURE.py
```

**Solución 1** - OBS Projector:
1. Verificar ventana "Proyector en ventana (Fuente) - Tibia_Fuente" abierta
2. Si no existe, crear en OBS: Clic derecho fuente → Proyector de ventana
3. Reiniciar bot

**Solución 2** - WebSocket:
1. OBS → Tools → WebSocket Server Settings
2. Verificar Enable WebSocket server = ✅
3. Server Port = 4455
4. Reiniciar OBS y bot

**Solución 3** - Minimap no visible:
1. En Tibia, verificar minimap NO está minimizado
2. Minimap debe estar en posición estándar (esquina superior derecha)
3. Reiniciar bot

**Solución 4** - Thresholds muy bajos:
1. Editar `src/repositories/radar/core.py`
2. Líneas ~70-75 (buscar "FENRIL_RADAR_CONFIDENCE")
3. Cambiar:
   - `default=0.60` → `default=0.75`
   - `default=0.40` → `default=0.55`
4. Reiniciar bot

### ❌ PROBLEMA: Refill loops infinitos

**Causa**: Configuración contradictoria waypoints

**Solución**:
```powershell
python FIX_CRITICAL_REFILL.py
```

Si persiste:
1. Abrir `file.json`
2. Buscar waypoint type="refill" (aprox línea 65):
   - `"ignore": false` (debe estar en false)
3. Buscar waypoint type="refillChecker" (aprox línea 105):
   - `"ignore": true` (debe estar en true para desactivar)
4. Guardar y reiniciar bot

### ❌ PROBLEMA: Bot no responde a INSERT

**Solución**:
```powershell
# Verificar proceso corriendo
Get-Process python

# Si hay múltiples, matar todos
taskkill /F /IM python.exe

# Reiniciar
python run_bot_persistent.py
```

### ❌ PROBLEMA: "Jump rejected: XXX sqm"

**Causa**: Radar detectó ubicación imposiblemente lejana

**Signos**:
- Saltos >200 sqm
- Coordenadas saltando entre ciudades

**Solución temporal**:
1. Bot tiene cache - seguirá con última coordenada conocida
2. Si persiste 10+ ticks → revisar captura OBS
3. Ejecutar `VALIDATE_OBS_CAPTURE.py`

**Solución definitiva**:
- Incrementar confidence thresholds (ver "coord=None" Solución 4)

### ❌ PROBLEMA: Bot stuck en un waypoint

**Causa**: Progress validation detectó no avance

**Logs esperados**:
```
[WalkToCoordinate] NO PROGRESS: Distance not decreasing (120.5 → 119.8 sqm). Recalculating path...
```

**Solución**:
- Sistema auto-recalcula automáticamente
- Esperar 15 segundos
- Si persiste → obstáculo físico (muro, puerta cerrada)
- Solución manual: mover personaje manualmente, presionar INSERT para reactivar

### ❌ PROBLEMA: OBS capture devuelve imágenes negras

**Diagnóstico**:
```powershell
# Ver últimas capturas
ls debug\dual_diag_radar_match_not_found_*_radar.png | sort LastWriteTime -Descending | select -First 5
```

**Solución**:
1. Verificar Tibia en primer plano o proyector OBS visible
2. Verificar fuente OBS capturando correctamente
3. Si Tibia usa Vulkan/DirectX 12 → cambiar a DirectX 11 en settings
4. Reiniciar OBS → Reiniciar Tibia → Reiniciar bot (en ese orden)

---

## CONFIGURACIÓN ÓPTIMA RECOMENDADA

### OBS Settings:
```
Source: "Tibia_Fuente" (Window Capture)
Capture Method: Windows 10+ (WGC)
Window: [TibiaClient.exe]: Tibia
Capture Cursor: No
Compatibility Mode: No

WebSocket:
Enable: Yes
Port: 4455
Authentication: No
```

### Tibia Settings:
```
Resolution: 1920x1009 (recomendado) o 1920x1080
Graphics Engine: DirectX 11 (mejor compatibilidad)
Fullscreen: No (windowed mode)
Minimap: Visible, posición default
```

### file.json Critical Settings:
```json
{
  "waypoints": {
    "items": [
      {"type": "walk", "label": "depot_exit", "ignore": false},
      ...
      {"type": "refill", "ignore": false},  // ← DEBE SER false
      {"type": "refillChecker", "ignore": true, "options": {  // ← DEBE SER true
        "minimumAmountOfManaPotions": 10,
        "minimumAmountOfCap": 50
      }}
    ]
  }
}
```

---

## LOGS ESPERADOS (FUNCIONAMIENTO NORMAL)

### Inicio exitoso:
```
[17:00:05][fenril][info] Paused (ng_pause=1)
[17:00:30][fenril][info] INSERT pressed - Bot PLAYING
[17:00:31][fenril][info] Tick reason changed: set task: walk
[17:00:32][fenril][info] coord=(32681, 31687, 6)
[17:00:33][fenril][info] Waypoint recalibrated: 2 -> 1 (distance: 15.2 sqm)
```

### Hunting normal:
```
[17:01:15][fenril][info] coord=(32659, 31664, 6)
[17:01:16][fenril][info] task=walkToWaypoint
[17:01:20][fenril][info] closestCreature detected
[17:01:21][fenril][info] task=attackClosestCreature
```

### Refill exitoso:
```
[17:05:30][fenril][info] coord=(32670, 31659, 6)
[17:05:31][fenril][info] task=refill
[17:05:32][fenril][info] task=enableChat
[17:05:33][fenril][info] task=say (hi)
[17:05:35][fenril][info] task=buyItem
[17:05:40][fenril][info] task=setNextWaypoint
```

### Logs problemáticos:
```
❌ coord=None persistente (>10 ticks)
❌ [fenril][dual] Diagnostics: radar match not found (repetitivo)
❌ Tick reason changed: radar jump rejected (frecuente)
❌ Tick reason changed: set task: refill (loop infinito)
```

---

## ORDEN DE TROUBLESHOOTING

Si el bot no funciona, seguir EN ORDEN:

1. ✅ **Ejecutar FIX_CRITICAL_REFILL.py** (1 min)
2. ✅ **Verificar OBS projector abierto** (30 seg)
3. ✅ **Ejecutar VALIDATE_OBS_CAPTURE.py** (1 min)
4. ✅ **Verificar minimap visible en Tibia** (10 seg)
5. ✅ **Reiniciar bot y probar 60 segundos** (2 min)
6. ⚠️ **Si coord=None → Incrementar thresholds** (5 min)
7. ⚠️ **Si persiste → Inspección visual debug/*.png** (10 min)

---

## CONTACTO Y SOPORTE

**Logs importantes para debugging**:
- Terminal output del bot
- Archivos en `debug/` (últimos 10 minutos)
- `file.json` (waypoints configuration)

**Comandos útiles de diagnóstico**:
```powershell
# Ver últimos diagnósticos radar
ls debug\dual_diag_*_radar.png | sort LastWriteTime -Descending | select -First 10

# Ver configuración waypoints
python check_waypoints.py

# Matar todos los procesos Python
taskkill /F /IM python.exe

# Ver procesos Python corriendo
Get-Process python
```

---

## TIEMPO ESTIMADO TROUBLESHOOTING

- **Refill loop**: 1 min (ejecutar script)
- **OBS capture básico**: 5 min (verificar projector + WebSocket)
- **coord=None simple**: 10 min (thresholds + restart)
- **coord=None complejo**: 30 min (inspección visual + ajustes)
- **First successful hunting cycle**: 15-30 min (configuración + prueba)

**TOTAL ESPERADO HASTA FUNCIONAMIENTO**: 30-60 minutos desde estado actual
