from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import slotIsAvailable, slotIsEquipped
from src.gameplay.typings import Context
from src.utils.safety import safe_int

tasksOrchestrator = TasksOrchestrator()

# TODO: add unit tests
def swapAmulet(context: Context) -> None:
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    if context['healing']['highPriority']['swapAmulet']['enabled'] == False:
        return
    currentTaskName = context['ng_tasksOrchestrator'].getCurrentTaskName(context)
    if currentTaskName in ['depositGold', 'refill', 'buyBackpack', 'selectChatTab', 'travel']:
        return
    status_bar = context.get('ng_statusBar') or {}
    swap_cfg = context.get('healing', {}).get('highPriority', {}).get('swapAmulet', {})
    hp_percentage = safe_int(status_bar.get('hpPercentage'), label="hpPercentage")
    tank_limit = safe_int(swap_cfg.get('tankAmulet', {}).get('hpPercentageLessThanOrEqual'), label="tankAmuletHpLimit")
    main_limit = safe_int(swap_cfg.get('mainAmulet', {}).get('hpPercentageGreaterThan'), label="mainAmuletHpLimit")
    if hp_percentage is None:
        return
    tank_slot = swap_cfg.get('tankAmulet', {}).get('slot')
    main_slot = swap_cfg.get('mainAmulet', {}).get('slot')
    if tank_slot is None or main_slot is None:
        return
    tankAmuletSlotIsEquipped = slotIsEquipped(context['ng_screenshot'], tank_slot)
    tankAmuletSlotIsAvailable = slotIsAvailable(context['ng_screenshot'], tank_slot)
    if tank_limit is not None and hp_percentage <= tank_limit:
        if not tankAmuletSlotIsEquipped and tankAmuletSlotIsAvailable:
            hotkey = swap_cfg.get('tankAmulet', {}).get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    mainAmuletSlotIsEquipped = slotIsEquipped(context['ng_screenshot'], main_slot)
    mainAmuletSlotIsAvailable = slotIsAvailable(context['ng_screenshot'], main_slot)
    if main_limit is not None and hp_percentage > main_limit:
        if not mainAmuletSlotIsEquipped and mainAmuletSlotIsAvailable:
            hotkey = swap_cfg.get('mainAmulet', {}).get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    if swap_cfg.get('tankAmuletAlwaysEquipped'):
        if not tankAmuletSlotIsEquipped and tankAmuletSlotIsAvailable:
            hotkey = swap_cfg.get('tankAmulet', {}).get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    if tankAmuletSlotIsEquipped:
        hotkey = swap_cfg.get('tankAmulet', {}).get('hotkey')
        if hotkey:
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    if mainAmuletSlotIsEquipped:
        hotkey = swap_cfg.get('mainAmulet', {}).get('hotkey')
        if hotkey:
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
