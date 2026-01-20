from src.gameplay.comboSpells.core import comboSpellDidMatch
from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.repositories.actionBar.core import hasCooldownByName
from src.repositories.gameWindow.creatures import getNearestCreaturesCount
from src.wiki.spells import spells
from .core.tasks.useComboHotkey import UseComboHotkeyTask
from .typings import Context
from src.utils.safety import safe_int


tasksOrchestrator = TasksOrchestrator()


# TODO: do not execute algorithm when has no combo spells
# TODO: add unit tests
# TODO: check if spell is casted, if not try cast again
def comboSpells(context: Context) -> None:
    status_bar = context.get('ng_statusBar') or {}
    healing_cfg = context.get('healing') or {}
    potions_cfg = healing_cfg.get('potions', {})
    mana = safe_int(status_bar.get('mana'), label="mana")
    if mana is None or context.get('ng_comboSpells', {}).get('enabled') == False:
        return
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    nearestCreaturesCount = getNearestCreaturesCount(
        context['gameWindow']['monsters'])
    if nearestCreaturesCount == 0:
        return
    hp_percentage = safe_int(status_bar.get('hpPercentage'), label="hpPercentage")
    hp_limit = safe_int(potions_cfg.get('firstHealthPotion', {}).get('hpPercentageLessThanOrEqual'), label="hpLimit")
    if hp_percentage is not None and hp_limit is not None and hp_percentage <= hp_limit:
        return
    mana_percentage = safe_int(status_bar.get('manaPercentage'), label="manaPercentage")
    if mana_percentage is not None and mana_percentage <= 30:
        return
    for key, comboSpell in enumerate(context['ng_comboSpells']['items']):
        if comboSpell['enabled'] == False:
            continue
        if comboSpellDidMatch(comboSpell, nearestCreaturesCount):
            spell = comboSpell['spells'][comboSpell['currentSpellIndex']]
            # TODO: JUST COMBO WHEN CAITING WITH PALADIN (NOT FOR NOW)
            if context['ng_cave']['isAttackingSomeCreature'] == False:
                return
            spell_info = spells.get(spell['name'])
            mana_needed = safe_int((spell_info.get('manaNeeded') if spell_info else None), label="comboManaNeeded")
            if mana_needed is None or mana < mana_needed:
                return
            # TODO: ADD SPELL CATEGORY IN WIKI
            if spell['name'] in ['utito tempo', 'utamo tempo']:
                if hasCooldownByName(context['ng_screenshot'], 'support'):
                    return
            else:
                if hasCooldownByName(context['ng_screenshot'], 'attack'):
                    return
            if hasCooldownByName(context['ng_screenshot'], spell['name']):
                return
            # TODO: verify if spell hotkey slot is available
            tasksOrchestrator.setRootTask(
                context, UseComboHotkeyTask(spell['hotkey'], spell['name']))
            return
