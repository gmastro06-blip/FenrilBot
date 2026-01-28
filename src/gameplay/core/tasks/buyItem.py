import src.repositories.refill.core as refillCore
from src.repositories.actionBar.core import getSlotCount
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.utils.console_log import log_throttled
import numpy as np


class BuyItemTask(BaseTask):
    def __init__(self: "BuyItemTask", itemName: str, itemQuantity: int, ignore: bool = False) -> None:
        super().__init__(delayOfTimeout=25.0)
        self.name = 'buyItem'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.timeout_config_path = 'ng_runtime.task_timeouts.buyItem'
        self.timeout_env_var = 'FENRIL_BUY_ITEM_TIMEOUT'
        self.timeout_default = 25.0
        self.shouldTimeoutTreeWhenTimeout = True
        self.itemName = itemName
        self.itemQuantity = itemQuantity
        self.ignore = ignore
        self._purchase_successful = False
        self._retry_count = 0
        self._max_retries = 3
        self._validation_state = 'NOT_STARTED'  # NOT_STARTED, IN_PROGRESS, SUCCESS, FAILED

    def shouldIgnore(self, _: Context) -> bool:
        if self.ignore == True:
            return True

        return self.itemQuantity <= 0

    def do(self, context: Context) -> Context:
        screenshot = context.get('ng_screenshot')
        if screenshot is None:
            self._validation_state = 'FAILED'
            return context

        # ESTADO: IN_PROGRESS
        self._validation_state = 'IN_PROGRESS'
        
        # Obtener slot de la poción para validación
        potion_slot = None
        if 'mana' in self.itemName.lower():
            potion_slot = context.get('healing', {}).get('potions', {}).get('firstManaPotion', {}).get('slot')
        elif 'health' in self.itemName.lower():
            potion_slot = context.get('healing', {}).get('potions', {}).get('firstHealthPotion', {}).get('slot')
        
        # VALIDACIÓN CRÍTICA 1: Contar potions ANTES
        potions_before = None
        validation_possible = False
        
        if potion_slot is not None:
            try:
                potions_before = getSlotCount(screenshot, potion_slot)
                if potions_before is not None:
                    validation_possible = True
            except Exception as e:
                log_throttled(
                    'buyItem.pre_validation_error',
                    'warn',
                    f'buyItem: Error reading potion count before purchase: {str(e)}',
                    5.0
                )
        
        # Si no podemos validar, abortamos inmediatamente
        if not validation_possible:
            self._validation_state = 'FAILED'
            self._retry_count += 1
            
            log_throttled(
                'buyItem.no_validation',
                'error',
                f'buyItem ABORT: Cannot validate purchase | item={self.itemName} qty={self.itemQuantity} | '
                f'retry={self._retry_count}/{self._max_retries} | reason=no_potion_slot | '
                f'slot_detected={potion_slot} | validation_state={self._validation_state}',
                2.0
            )
            
            if self._retry_count >= self._max_retries:
                self._purchase_successful = False
            
            return context
        
        # Ejecutar compra
        purchase_executed = False
        use_modern_ui = False
        
        if isinstance(screenshot, np.ndarray):
            try:
                if refillCore.getTradeBottomPos(screenshot) is None:
                    use_modern_ui = True
            except Exception:
                use_modern_ui = True

        if use_modern_ui:
            from src.repositories.refill.modern_ui import buyItemModern
            purchase_executed = buyItemModern(screenshot, self.itemName, self.itemQuantity)
        else:
            refillCore.buyItem(screenshot, self.itemName, self.itemQuantity)
            purchase_executed = True  # Legacy no retorna bool
        
        if not purchase_executed:
            self._validation_state = 'FAILED'
            self._retry_count += 1
            
            log_throttled(
                'buyItem.execution_failed',
                'error',
                f'buyItem EXECUTION FAILED | item={self.itemName} qty={self.itemQuantity} | '
                f'retry={self._retry_count}/{self._max_retries} | reason=purchase_returned_false | '
                f'modern_ui={use_modern_ui} | validation_state={self._validation_state}',
                2.0
            )
            
            if self._retry_count >= self._max_retries:
                self._purchase_successful = False
            
            return context
        
        # VALIDACIÓN CRÍTICA 2: Verificar aumento de inventory
        from time import sleep
        from src.utils.core import getScreenshot
        
        # HARDENING: Adaptive wait con retry para inventory update
        # Timeout máximo 3s, check cada 0.5s
        new_screenshot = None
        max_wait_attempts = 6  # 6 * 0.5s = 3s max
        for wait_attempt in range(max_wait_attempts):
            sleep(0.5)
            new_screenshot = getScreenshot()
            
            # Si screenshot es válido, salir early
            if new_screenshot is not None:
                # Dar un último delay de estabilización
                if wait_attempt < 2:  # Si fue muy rápido, esperar mínimo 1s total
                    sleep(0.5)
                break
        
        if new_screenshot is None:
            self._validation_state = 'FAILED'
            self._retry_count += 1
            
            log_throttled(
                'buyItem.post_screenshot_failed',
                'error',
                f'buyItem POST-SCREENSHOT FAILED | item={self.itemName} qty={self.itemQuantity} | '
                f'retry={self._retry_count}/{self._max_retries} | reason=screenshot_capture_failed | '
                f'wait_attempts={max_wait_attempts} | validation_state={self._validation_state}',
                2.0
            )
            
            if self._retry_count >= self._max_retries:
                self._purchase_successful = False
            
            return context
        
        try:
            # Type assertion: potion_slot is guaranteed not None (early return on line 70)
            assert potion_slot is not None
            potions_after = getSlotCount(new_screenshot, potion_slot)
            
            if potions_after is None:
                # No se pudo leer el slot después
                self._validation_state = 'FAILED'
                self._retry_count += 1
                
                log_throttled(
                    'buyItem.post_count_failed',
                    'error',
                    f'buyItem POST-COUNT FAILED | item={self.itemName} qty={self.itemQuantity} | '
                    f'retry={self._retry_count}/{self._max_retries} | reason=cannot_read_slot_after | '
                    f'slot={potion_slot} | validation_state={self._validation_state}',
                    2.0
                )
                
                if self._retry_count >= self._max_retries:
                    self._purchase_successful = False
                
                return context
            
            # CRITERIO DE ÉXITO INEQUÍVOCO
            # Type assertion: potions_before is not None (guaranteed by early return on line 70)
            assert potions_before is not None
            
            expected_increase = self.itemQuantity
            actual_increase = potions_after - potions_before
            
            # PROTECCIÓN: Si el usuario consumió pociones durante la compra,
            # potions_after podría ser menor. En ese caso, validamos que al menos
            # hay MÁS que el mínimo absoluto esperado.
            minimum_absolute = potions_before + int(expected_increase * 0.5)
            
            # Tolerancia: al menos 50% de aumento O cantidad absoluta razonable
            if actual_increase >= int(expected_increase * 0.5) or potions_after >= minimum_absolute:
                # SUCCESS: Compra verificada objetivamente
                self._validation_state = 'SUCCESS'
                self._purchase_successful = True
                self._retry_count = 0  # Reset para futuras compras
                
                log_throttled(
                    'buyItem.success_verified',
                    'info',
                    f'buyItem SUCCESS | item={self.itemName} qty={self.itemQuantity} | '
                    f'inventory={potions_before}→{potions_after} | increase={actual_increase} (expected={expected_increase}) | '
                    f'criteria_met={"increase" if actual_increase >= int(expected_increase * 0.5) else "absolute"} | '
                    f'validation_state={self._validation_state}',
                    5.0
                )
            else:
                # FAILED: No se detectó aumento suficiente
                self._validation_state = 'FAILED'
                self._retry_count += 1
                
                log_throttled(
                    'buyItem.validation_failed',
                    'error',
                    f'buyItem VALIDATION FAILED | item={self.itemName} qty={self.itemQuantity} | '
                    f'retry={self._retry_count}/{self._max_retries} | '
                    f'inventory={potions_before}→{potions_after} | increase={actual_increase} (expected={expected_increase}) | '
                    f'min_increase={int(expected_increase * 0.5)} | min_absolute={minimum_absolute} | '
                    f'validation_state={self._validation_state}',
                    2.0
                )
                
                if self._retry_count >= self._max_retries:
                    self._purchase_successful = False
        
        except Exception as e:
            self._validation_state = 'FAILED'
            self._retry_count += 1
            
            log_throttled(
                'buyItem.validation_exception',
                'error',
                f'buyItem: Validation exception: {str(e)}. Retry {self._retry_count}/{self._max_retries}',
                2.0
            )
            
            if self._retry_count >= self._max_retries:
                self._purchase_successful = False
        
        return context

    def did(self, context: Context) -> bool:
        if self.ignore == True:
            return True
        if self.itemQuantity <= 0:
            return True
        
        # ESTADO FINAL: Solo SUCCESS o agotamiento de retries permite continuar
        if self._validation_state == 'SUCCESS':
            return True
        
        if self._retry_count >= self._max_retries:
            # Agotamos reintentos, marcar como completado pero fallido
            log_throttled(
                'buyItem.max_retries_exhausted',
                'error',
                f'buyItem: Max retries ({self._max_retries}) exhausted for {self.itemName}. Purchase FAILED definitively.',
                10.0
            )
            # Devolver True para no bloquear el flujo, pero refill detectará el fallo
            return True
        
        # Si está en progreso o falló pero tiene retries, no está completo
        return False
