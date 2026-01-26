import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
import src.repositories.inventory.core as inventoryCore
import src.utils.core as coreUtils
from src.repositories.inventory.core import images
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
        if inventoryCore.isContainerOpen(screenshot, 'locker'):
            return True

        # Extra signal: the depot icon lives inside the locker UI.
        # If we can see it, the locker is open even if the container bar template
        # didn't match (common under scaling/theme changes).
        try:
            tpl = images['slots']['depot']
            if coreUtils.locate(screenshot, tpl, confidence=0.78) is not None:
                return True
            if coreUtils.locateMultiScale(
                screenshot,
                tpl,
                confidence=0.78,
                scales=(0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15),
            ) is not None:
                return True
        except Exception:
            pass
        return False

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