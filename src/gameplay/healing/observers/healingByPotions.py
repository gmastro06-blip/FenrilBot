from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import slotIsAvailable
from src.gameplay.typings import Context
from ..utils.potions import matchHpHealing


tasksOrchestrator = TasksOrchestrator()


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
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=1))
            return