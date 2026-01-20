from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.gameplay.core.tasks.useSpellHealHotkey import UseSpellHealHotkeyTask
from src.repositories.actionBar.core import hasCooldownByName
from src.wiki.spells import spells
from src.gameplay.typings import Context
from src.utils.safety import safe_int


tasksOrchestrator = TasksOrchestrator()


# TODO: add unit tests
def healingBySpells(context: Context) -> None:
    status_bar = context.get('ng_statusBar') or {}
    healing_cfg = context.get('healing') or {}
    potions_cfg = healing_cfg.get('potions', {})
    spells_cfg = healing_cfg.get('spells', {})

    hp_percentage = safe_int(status_bar.get('hpPercentage'), label="hpPercentage")
    mana_percentage = safe_int(status_bar.get('manaPercentage'), label="manaPercentage")
    mana = safe_int(status_bar.get('mana'), label="mana")
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
    if hp_percentage is None or mana is None:
        return
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    critical_cfg = spells_cfg.get('criticalHealing', {})
    if critical_cfg.get('enabled'):
        critical_limit = safe_int(critical_cfg.get('hpPercentageLessThanOrEqual'), label="criticalHpLimit")
        critical_spell = critical_cfg.get('spell')
        critical_info = spells.get(critical_spell or "")
        mana_needed = safe_int((critical_info.get('manaNeeded') if critical_info else None), label="criticalManaNeeded")
        if (
            critical_limit is not None
            and hp_percentage <= critical_limit
            and mana_needed is not None
            and mana >= mana_needed
            and critical_spell
            and not hasCooldownByName(context['ng_screenshot'], critical_spell)
        ):
            hotkey = critical_cfg.get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey))
            return
    light_cfg = spells_cfg.get('lightHealing', {})
    if light_cfg.get('enabled'):
        light_limit = safe_int(light_cfg.get('hpPercentageLessThanOrEqual'), label="lightHpLimit")
        light_spell = light_cfg.get('spell')
        light_info = spells.get(light_spell or "")
        mana_needed = safe_int((light_info.get('manaNeeded') if light_info else None), label="lightManaNeeded")
        if (
            light_limit is not None
            and hp_percentage <= light_limit
            and mana_needed is not None
            and mana >= mana_needed
            and light_spell
            and not hasCooldownByName(context['ng_screenshot'], light_spell)
        ):
            hotkey = light_cfg.get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseSpellHealHotkeyTask(hotkey))
            return
    utura_cfg = spells_cfg.get('utura', {})
    if utura_cfg.get('enabled'):
        utura_info = spells.get('utura')
        mana_needed = safe_int((utura_info.get('manaNeeded') if utura_info else None), label="uturaManaNeeded")
        if mana_needed is not None and mana >= mana_needed and not hasCooldownByName(context['ng_screenshot'], 'utura'):
            hotkey = utura_cfg.get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey))
            return
    utura_gran_cfg = spells_cfg.get('uturaGran', {})
    if utura_gran_cfg.get('enabled'):
        utura_gran_info = spells.get('utura gran')
        mana_needed = safe_int((utura_gran_info.get('manaNeeded') if utura_gran_info else None), label="uturaGranManaNeeded")
        if mana_needed is not None and mana >= mana_needed and not hasCooldownByName(context['ng_screenshot'], 'utura gran'):
            hotkey = utura_gran_cfg.get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey))
