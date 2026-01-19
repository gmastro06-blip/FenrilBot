from src.gameplay.core.tasks.orchestrator import TasksOrchestrator
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.repositories.actionBar.core import slotIsAvailable, slotIsEquipped
from src.gameplay.typings import Context
from src.utils.safety import safe_int

tasksOrchestrator = TasksOrchestrator()

# TODO: add unit tests
def swapRing(context: Context) -> None:
    currentTask = tasksOrchestrator.getCurrentTask(context)
    if currentTask is not None:
        if currentTask.status == 'completed':
            tasksOrchestrator.reset()
        else:
            tasksOrchestrator.do(context)
            return
    if context['healing']['highPriority']['swapRing']['enabled'] == False:
        return
    currentTaskName = context['ng_tasksOrchestrator'].getCurrentTaskName(context)
    if currentTaskName in ['depositGold', 'refill', 'buyBackpack', 'selectChatTab', 'travel']:
        return
    status_bar = context.get('ng_statusBar') or {}
    swap_cfg = context.get('healing', {}).get('highPriority', {}).get('swapRing', {})
    hp_percentage = safe_int(status_bar.get('hpPercentage'), label="hpPercentage")
    tank_limit = safe_int(swap_cfg.get('tankRing', {}).get('hpPercentageLessThanOrEqual'), label="tankRingHpLimit")
    main_limit = safe_int(swap_cfg.get('mainRing', {}).get('hpPercentageGreaterThan'), label="mainRingHpLimit")
    if hp_percentage is None:
        return
    tank_slot = swap_cfg.get('tankRing', {}).get('slot')
    main_slot = swap_cfg.get('mainRing', {}).get('slot')
    if tank_slot is None or main_slot is None:
        return
    tankRingSlotIsEquipped = slotIsEquipped(context['ng_screenshot'], tank_slot)
    tankRingSlotIsAvailable = slotIsAvailable(context['ng_screenshot'], tank_slot)
    if tank_limit is not None and hp_percentage <= tank_limit:
        if not tankRingSlotIsEquipped and tankRingSlotIsAvailable:
            hotkey = swap_cfg.get('tankRing', {}).get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    mainRingSlotIsEquipped = slotIsEquipped(context['ng_screenshot'], main_slot)
    mainRingSlotIsAvailable = slotIsAvailable(context['ng_screenshot'], main_slot)
    if main_limit is not None and hp_percentage > main_limit:
        if not mainRingSlotIsEquipped and mainRingSlotIsAvailable:
            hotkey = swap_cfg.get('mainRing', {}).get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    if swap_cfg.get('tankRingAlwaysEquipped'):
        if not tankRingSlotIsEquipped and tankRingSlotIsAvailable:
            hotkey = swap_cfg.get('tankRing', {}).get('hotkey')
            if hotkey:
                tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    if tankRingSlotIsEquipped:
        hotkey = swap_cfg.get('tankRing', {}).get('hotkey')
        if hotkey:
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
        return
    if mainRingSlotIsEquipped:
        hotkey = swap_cfg.get('mainRing', {}).get('hotkey')
        if hotkey:
            tasksOrchestrator.setRootTask(context, UseHotkeyTask(hotkey, delayAfterComplete=2))
