import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
import src.repositories.inventory.core as inventoryCore
from ...typings import Context
from .common.base import BaseTask


class OpenLockerTask(BaseTask):
    def __init__(self: "OpenLockerTask") -> None:
        super().__init__(delayOfTimeout=12.0)
        self.name = 'openLocker'
        self.delayAfterComplete = 1
        self.timeout_config_path = 'ng_runtime.task_timeouts.openLocker'
        self.timeout_env_var = 'FENRIL_OPEN_LOCKER_TIMEOUT'
        self.timeout_default = 12.0
        # If we can't open the locker, don't stall the whole cavebot forever.
        self.shouldTimeoutTreeWhenTimeout = True

    def shouldIgnore(self, context: Context) -> bool:
        screenshot = context.get('ng_screenshot') if isinstance(context, dict) else None
        if screenshot is None:
            return False
        return inventoryCore.isContainerOpen(screenshot, 'locker')

    def do(self, context: Context) -> Context:
        current_coord = context.get('ng_radar', {}).get('coordinate')
        locker_coord = context.get('ng_deposit', {}).get('lockerCoordinate')
        game_window_pos = context.get('gameWindow', {}).get('coordinate')
        if current_coord is None or locker_coord is None or game_window_pos is None:
            return context

        slot = gameWindowCore.getSlotFromCoordinate(current_coord, locker_coord)
        if slot is None:
            return context

        gameWindowSlot.rightClickSlot(slot, game_window_pos)
        return context

    def did(self, context: Context) -> bool:
        return self.shouldIgnore(context)
    
    def onComplete(self, context: Context) -> Context:
        context['ng_deposit']['lockerCoordinate'] = None
        return context