import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
from src.shared.typings import Waypoint
from ...typings import Context
from .common.base import BaseTask
from time import sleep

class RightClickUseTask(BaseTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__()
        self.name = 'rightClickUse'
        self.waypoint = waypoint

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
