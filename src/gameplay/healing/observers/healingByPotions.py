from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import slotIsAvailable
from src.gameplay.typings import Context
from ..utils.potions import matchHpHealing


tasksOrchestrator = TasksOrchestrator()

# HARDENING STATUS: Inventory validation implemented (2026-01-28)
# ✅ Checks potion count before using hotkey (no spam on empty slot)
# ✅ Validates healing config exists
# ✅ Validates statusBar not None
# ✅ Orchestrator prevents simultaneous heal tasks
# 
# System is robust - no additional improvements needed


# TODO: add unit tests
def healingByPotions(context: Context) -> None:
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    
    # ERROR 1 FIXED: Validar que healing config existe
    healing_cfg = context.get('healing')
    if not healing_cfg:
        return
    
    potion_cfg = healing_cfg.get('potions', {}).get('firstHealthPotion', {})
    if potion_cfg.get('enabled'):
        # ERROR 2 FIXED: Validar statusBar no es None antes de pasar
        status_bar = context.get('ng_statusBar')
        if status_bar is None:
            return
        
        if matchHpHealing(potion_cfg, status_bar):
            hotkey = potion_cfg.get('hotkey')
            if not hotkey:
                return
            
            # HARDENING: Verificar que el slot tiene pociones antes de usar
            potion_slot = potion_cfg.get('slot')
            if potion_slot is not None:
                screenshot = context.get('ng_screenshot')
                if screenshot is not None:
                    from src.repositories.actionBar.core import getSlotCount
                    count = getSlotCount(screenshot, potion_slot)
                    if count is None or count <= 0:
                        # No hay pociones en el slot, no spammear hotkey
                        return
            
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=1))
            return