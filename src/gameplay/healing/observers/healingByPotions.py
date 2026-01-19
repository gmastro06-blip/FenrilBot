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
    potion_cfg = context['healing']['potions'].get('firstHealthPotion', {})
    if potion_cfg.get('enabled'):
        # if matchHpHealing(context['healing']['potions']['firstHealthPotion'], context['ng_statusBar']) and slotIsAvailable(context['ng_screenshot'], context['healing']['potions']['firstHealthPotion']['slot']):
        if matchHpHealing(potion_cfg, context.get('ng_statusBar')):
            hotkey = potion_cfg.get('hotkey')
            if not hotkey:
                return
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=1))
            return