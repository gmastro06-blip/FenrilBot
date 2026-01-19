from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import slotIsAvailable
from src.gameplay.typings import Context
from src.utils.safety import safe_int
from ..utils.potions import matchManaHealing


tasksOrchestrator = TasksOrchestrator()


# TODO: add unit tests
def healingByMana(context: Context) -> None:
    status_bar = context.get('ng_statusBar') or {}
    potions_cfg = context.get('healing', {}).get('potions', {})
    hp_percentage = safe_int(status_bar.get('hpPercentage'), label="hpPercentage")
    hp_limit = safe_int(potions_cfg.get('firstHealthPotion', {}).get('hpPercentageLessThanOrEqual'), label="hpLimit")
    if (
        hp_percentage is not None
        and hp_limit is not None
        and hp_percentage <= hp_limit
        and potions_cfg.get('firstHealthPotion', {}).get('enabled')
    ):
        return
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    mana_potion_cfg = potions_cfg.get('firstManaPotion', {})
    if mana_potion_cfg.get('enabled'):
        # if matchManaHealing(context['healing']['potions']['firstManaPotion'], context['ng_statusBar']) and slotIsAvailable(context['ng_screenshot'], context['healing']['potions']['firstManaPotion']['slot']):
        if matchManaHealing(mana_potion_cfg, status_bar):
            hotkey = mana_potion_cfg.get('hotkey')
            if not hotkey:
                return
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=1))
            return
