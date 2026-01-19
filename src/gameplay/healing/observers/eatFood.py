from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import slotIsAvailable, slotIsEquipped
from src.repositories.skills.core import getFood
from src.gameplay.typings import Context
from src.utils.safety import safe_int


tasksOrchestrator = TasksOrchestrator()


# TODO: add unit tests
def eatFood(context: Context) -> None:
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    if not context['healing']['eatFood']['enabled']:
        return
    food = safe_int(getFood(context['ng_screenshot']), label="food")
    food_limit = safe_int(context.get('healing', {}).get('eatFood', {}).get('eatWhenFoodIslessOrEqual'), label="foodLimit")
    if food is None or food_limit is None:
        return
    if food > food_limit:
        return
    tasksOrchestrator.setRootTask(
        context, UseHotkeyTask(context['healing']['eatFood']['hotkey'], delayAfterComplete=2))
