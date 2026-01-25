import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
from src.shared.typings import Waypoint
from ...typings import Context
from .common.base import BaseTask
from time import sleep
from typing import Optional

class RightClickUseTask(BaseTask):
    def __init__(self, waypoint: Waypoint, expectedZ: Optional[int] = None):
        super().__init__()
        self.name = 'rightClickUse'
        self.waypoint = waypoint
        self.expectedZ = expectedZ

        if expectedZ is not None:
            # If we expect a floor change (e.g. ladder), failing should abort the whole waypoint task.
            self.shouldTimeoutTreeWhenTimeout = True

            # Runtime-configurable timeout.
            self.timeout_config_path = 'ng_runtime.task_timeouts.rightClickUse'
            self.timeout_env_var = 'FENRIL_TIMEOUT_RIGHT_CLICK_USE'
            self.timeout_default = 6.0

    def do(self, context: Context) -> Context:
        current_coord = context.get('ng_radar', {}).get('coordinate')
        game_window_pos = context.get('gameWindow', {}).get('coordinate')
        if current_coord is None or game_window_pos is None:
            return context

        slot = gameWindowCore.getSlotFromCoordinate(current_coord, self.waypoint['coordinate'])
        if slot is None:
            return context

        sleep(0.2)
        gameWindowSlot.rightClickSlot(slot, game_window_pos)
        sleep(0.2)
        return context

    def did(self, context: Context) -> bool:
        if self.expectedZ is None:
            return True
        coord = context.get('ng_radar', {}).get('coordinate')
        if coord is None:
            return False
        try:
            return int(coord[2]) == int(self.expectedZ)
        except Exception:
            return False
