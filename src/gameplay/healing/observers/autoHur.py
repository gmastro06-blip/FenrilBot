from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import hasCooldownByName
from src.wiki.spells import spells
from src.gameplay.typings import Context
from src.utils.safety import safe_int

tasksOrchestrator = TasksOrchestrator()

# TODO: add unit tests
def autoHur(context: Context) -> None:
    status_bar = context.get('ng_statusBar') or {}
    potions_cfg = context.get('healing', {}).get('potions', {})
    hp_percentage = safe_int(status_bar.get('hpPercentage'), label="hpPercentage")
    mana_percentage = safe_int(status_bar.get('manaPercentage'), label="manaPercentage")
    hp_limit = safe_int(potions_cfg.get('firstHealthPotion', {}).get('hpPercentageLessThanOrEqual'), label="hpLimit")
    if (
        hp_percentage is not None
        and hp_limit is not None
        and hp_percentage <= hp_limit
        and potions_cfg.get('firstHealthPotion', {}).get('enabled')
    ):
        return
    if (
        mana_percentage is not None
        and mana_percentage <= 30
        and potions_cfg.get('firstManaPotion', {}).get('enabled')
    ):
        return
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    if not context['auto_hur']['enabled']:
        return
    if context['statsBar']['hur'] is not None and context['statsBar']['hur'] == True:
        return
    if context['auto_hur']['pz'] == False and context['statsBar']['pz'] is not None and context['statsBar']['pz'] == True:
        return
    currentTaskName = context['ng_tasksOrchestrator'].getCurrentTaskName(context)
    if currentTaskName in ['attackClosestCreature', 'lootMonstersBox', 'refill', 'buyBackpack', 'useRopeWaypoint', 'useShovelWaypoint', 'rightClickUseWaypoint', 'openDoor', 'useLadderWaypoint']:
        return
    if hasCooldownByName(context['ng_screenshot'], 'support'):
        return
    spell_name = context.get('auto_hur', {}).get('spell')
    if not spell_name:
        return
    if hasCooldownByName(context['ng_screenshot'], spell_name):
        return
    mana = safe_int(status_bar.get('mana'), label="mana")
    mana_needed = safe_int(spells.get(spell_name, {}).get('manaNeeded'), label="autoHurManaNeeded")
    if mana is None or mana_needed is None or mana < mana_needed:
        return
    hotkey = context.get('auto_hur', {}).get('hotkey')
    if not hotkey:
        return
    tasksOrchestrator.setRootTask(
        context, UseHotkeyTask(hotkey, delayAfterComplete=1))
