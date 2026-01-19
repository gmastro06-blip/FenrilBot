from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import hasCooldownByName
from src.wiki.spells import spells
from src.gameplay.typings import Context
from src.utils.safety import safe_int

tasksOrchestrator = TasksOrchestrator()

# TODO: add unit tests
def clearPoison(context: Context) -> None:
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    if not context['clear_stats']['poison']:
        return
    if context['statsBar']['poison'] is not None and context['statsBar']['poison'] == False:
        return
    if hasCooldownByName(context['ng_screenshot'], 'exana pox'):
        return
    mana = safe_int((context.get('ng_statusBar') or {}).get('mana'), label="mana")
    mana_needed = safe_int(spells.get('exana pox', {}).get('manaNeeded'), label="exanaPoxManaNeeded")
    if mana is None or mana_needed is None or mana < mana_needed:
        return
    tasksOrchestrator.setRootTask(
        context, UseHotkeyTask(context['clear_stats']['poison_hotkey'], delayAfterComplete=1))
