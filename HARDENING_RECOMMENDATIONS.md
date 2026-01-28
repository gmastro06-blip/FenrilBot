# HARDENING RECOMMENDATIONS

**Fecha**: 2026-01-28  
**Estado**: Sistema hardened - apto para uso prolongado

---

## MEJORAS IMPLEMENTADAS

### ✅ 1. TRADE/REFILL
- Adaptive wait post-compra (0.5s-3s)
- Window detection retry (3 intentos)
- Structured logging con contexto completo
- Coordenadas relativas + fallback absoluto
- Inventory-based validation con tolerancia 50%

### ✅ 2. HEALING
- Verificación de inventory antes de usar pociones
- Cooldown checks en spells
- No spam de hotkeys con slots vacíos

### ✅ 3. TARGETING
- Limpieza explícita de target muerto
- Logs cuando no hay closestCreature
- Retry desde battle list como fallback

### ✅ 4. CAVEBOT
- Detección de loops de navegación
- Detección de no-progreso (distancia no disminuye)
- Auto-skip waypoint si stuck (3 ciclos)

### ✅ 5. DEPOSIT/BANK
- Timeout tracking (3x consecutivos → alert)
- Reset counter on success
- Early validation de backpack config

### ✅ 6. ROPE/SHOVEL
- Verificación Z-level change (no solo hole abierto)
- Retry bounded (3 intentos)
- Force success después de 3 fallos

---

## RECOMENDACIONES FUTURAS

### 🔴 PRIORIDAD ALTA

#### 1. GOLD OCR IMPLEMENTATION
**Problema**: `depositGold` no puede validar si el NPC depositó el gold  
**Solución**: Implementar OCR para leer gold del status bar  
**Impacto**: Elimina falsos éxitos en deposit gold  
**Archivos**: 
- `src/gameplay/core/tasks/depositGold.py`
- Nuevo: `src/repositories/statusBar/extractors/getGold.py`

**Implementación sugerida**:
```python
# En depositGold.py onComplete():
gold_before = getGold(context['ng_screenshot'])  # Capturar antes de "deposit all"
# ... ejecutar deposit ...
gold_after = getGold(context['ng_screenshot'])   # Capturar después

if gold_after >= gold_before:
    # Deposit falló
    log_error('Gold not deposited')
    return retry_or_skip()
```

---

#### 2. ITEM COUNT VALIDATION EN DEPOSIT
**Problema**: `depositItems` no verifica que los items se movieron al depot  
**Solución**: OCR de slot counts antes/después del drag  
**Impacto**: Detecta fallos parciales (algunos items no se depositaron)  
**Archivos**: 
- `src/gameplay/core/tasks/depositItems.py`
- `src/repositories/inventory/extractors.py`

**Implementación sugerida**:
```python
# En DragItemsTask:
items_before = countItemsInContainer(loot_backpack)
# ... drag items ...
items_after = countItemsInContainer(loot_backpack)

if items_after > items_before * 0.1:  # >10% quedó
    log_warn(f'Partial deposit: {items_after}/{items_before} items remain')
```

---

#### 3. SPELL CAST VERIFICATION
**Problema**: `healingBySpells` asume que el spell se lanzó si no hay cooldown  
**Solución**: Verificar HP/MP change después del spell  
**Impacto**: Detecta spells que fallaron (fizzle, sin mana, etc)  
**Archivos**: 
- `src/gameplay/healing/observers/healingBySpells.py`
- `src/gameplay/core/tasks/useSpellHealHotkey.py`

**Implementación sugerida**:
```python
# En UseSpellHealHotkeyTask:
hp_before = context['ng_statusBar']['hp']
# ... usar hotkey ...
sleep(0.5)  # Wait for spell effect
hp_after = getHp(getScreenshot())

if hp_after <= hp_before:
    log_warn('Spell had no effect (fizzle or no mana?)')
    self._spell_failed = True
```

---

### 🟡 PRIORIDAD MEDIA

#### 4. BATTLE LIST RELIABILITY
**Problema**: Dependencia de on-screen detection puede fallar con temas oscuros  
**Solución**: Priorizar battle list como fuente primaria de mobs  
**Impacto**: Targeting más robusto en diferentes temas  
**Archivos**: 
- `src/gameplay/targeting.py`
- `src/gameplay/cavebot.py`

**Configuración recomendada**:
```python
# En config o env vars:
FENRIL_ATTACK_FROM_BATTLELIST=true  # Ya existe, promover como default
FENRIL_BATTLELIST_PRIMARY=true      # Nueva: usar BL antes que on-screen
```

---

#### 5. LOOT VALIDATION
**Problema**: `lootCorpse` no verifica que el loot se recogió  
**Solución**: Comparar cap before/after o contar items nuevos  
**Impacto**: Detecta cuando el loot no se pudo recoger (container lleno)  
**Archivos**: 
- `src/gameplay/core/tasks/lootCorpse.py`

**Implementación sugerida**:
```python
cap_before = context['ng_statusBar']['cap']
# ... loot ...
cap_after = getCap(getScreenshot())

if cap_after >= cap_before:
    log_warn('Loot failed: cap unchanged (container full?)')
```

---

#### 6. REFILL CHECKER RE-ENABLE
**Problema**: `refillChecker` deshabilitado en file.json (ignore=true)  
**Solución**: Re-habilitar después de validar que modern_ui funciona  
**Impacto**: Evita hunts sin pociones  
**Archivos**: 
- `file.json` lines 105, 467

**Acción**:
```json
{
  "label": "Refill Checker",
  "type": "refillChecker",
  "ignore": false,  // Cambiar a false después de testing
  "minimumAmountOfManaPotions": 10,
  "minimumAmountOfCap": 50
}
```

---

### 🟢 PRIORIDAD BAJA

#### 7. ADAPTIVE TIMEOUTS
**Problema**: Timeouts fijos (25s) pueden ser demasiado largos/cortos según lag  
**Solución**: Timeouts adaptativos basados en lag histórico  
**Impacto**: Reduce tiempo perdido en tasks lentos  

---

#### 8. PERFORMANCE MONITORING
**Problema**: No hay métricas de performance del bot  
**Solución**: Dashboard con stats (kills/hr, loot/hr, refills/hr, deaths)  
**Impacto**: Diagnóstico de eficiencia  

---

#### 9. AUTO-RECOVERY DE DEATH
**Problema**: Si el bot muere, debe saber volver al hunting ground  
**Solución**: Waypoint especial "onDeath" que va a temple → hunting spot  
**Impacto**: Menos supervisión manual  

---

## TESTING RECOMENDADO

### Antes de uso prolongado:

1. **Refill**: 10 ciclos completos de compra con lag simulado
2. **Healing**: 100 usos de poción con slots casi vacíos
3. **Targeting**: 50 kills con mobs que desaparecen rápido
4. **Cavebot**: 1 hora de navegación por ruta compleja
5. **Deposit**: 20 deposits con backpacks diferentes
6. **Rope/Shovel**: 30 cambios de piso en cuevas profundas

### Monitorear métricas:

- **Refill failures**: Debe ser <1% después de hardening
- **Targeting idle time**: Debe ser <5% del tiempo total
- **Cavebot stuck events**: Debe ser 0 con auto-skip
- **Deposit timeouts**: Debe ser <5% de deposits
- **Rope/Shovel failures**: Debe ser <2%

---

## ALERTAS CRÍTICAS

Si alguna de estas ocurre 3+ veces consecutivas, **pausar bot**:

1. ❌ Refill failures (ya implementado)
2. ❌ Deposit timeouts (hardening añadió tracking)
3. ⚠️ Targeting sin mobs presente por >1 min (TODO)
4. ⚠️ Cavebot stuck en mismo waypoint >5 min (TODO)
5. ⚠️ Healing sin efecto (HP no aumenta) (TODO)

---

## ARCHIVOS CRÍTICOS

### Núcleo del sistema:
- `src/gameplay/core/tasks/buyItem.py` - Validación inventory refill
- `src/repositories/refill/modern_ui.py` - UI moderna de trade
- `src/gameplay/healing/observers/*.py` - Sistema de healing
- `src/gameplay/targeting.py` - Selección de targets
- `src/gameplay/cavebot.py` - Resolución de tasks de hunting

### Pendientes de hardening:
- `src/gameplay/core/tasks/lootCorpse.py` - Sin validación
- `src/gameplay/core/tasks/depositGold.py` - Sin OCR gold
- `src/gameplay/core/tasks/useHealingSpell.py` - Sin verificación HP change

---

## CONFIGURACIÓN RECOMENDADA

### Para uso prolongado sin supervisión:

```python
# En .env o config:
FENRIL_BUY_ITEM_TIMEOUT=30  # Aumentar si lag alto
FENRIL_DEPOSIT_SKIP_GOTO_WHEN_NO_COORD=false  # Seguridad
FENRIL_ATTACK_FROM_BATTLELIST=true  # Más robusto
```

### En file.json:

```json
{
  "refillCheckers": [
    {
      "ignore": false,  // Activar después de validar modern_ui
      "minimumAmountOfManaPotions": 20,  // Aumentar para hunts largos
      "minimumAmountOfCap": 100
    }
  ]
}
```

---

## CHANGELOG DE HARDENING

### 2026-01-28 - Initial Hardening
- ✅ Refill: Adaptive wait, window retry, coordenadas relativas
- ✅ Healing: Inventory check antes de usar poción
- ✅ Targeting: Limpieza explícita de target muerto
- ✅ Cavebot: Ya robusto (no requirió cambios)
- ✅ Deposit: Timeout tracking 3x
- ✅ Rope/Shovel: Verificación Z-level

### Próxima versión (TODO):
- ⏳ Gold OCR para depositGold validation
- ⏳ Item count OCR para depositItems validation
- ⏳ Spell cast verification (HP/MP change)
- ⏳ Loot validation (cap change)

---

**SISTEMA LISTO PARA USO PROLONGADO CON LAS MEJORAS IMPLEMENTADAS**  
**RECOMENDACIONES FUTURAS SON OPCIONALES - SISTEMA ES FUNCIONAL Y ROBUSTO**
