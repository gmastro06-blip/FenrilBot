from typing import Any
import os

from src.gameplay.typings import Context
from src.gameplay.utils import coordinatesAreEqual
import src.repositories.gameWindow.slot as gameWindowSlot
import src.utils.keyboard as utilsKeyboard
from .common.base import BaseTask
from src.utils.runtime_settings import get_str


# TODO: check if something was looted or exactly count was looted
class CollectDeadCorpseTask(BaseTask):
    def __init__(self: "CollectDeadCorpseTask", creature: Any) -> None:
        super().__init__()
        self.name = 'collectDeadCorpse'
        self.delayBeforeStart = 0.85
        self.creature = creature

    def do(self, context: Context) -> Context:
        loot_modifier = get_str(context, 'ng_runtime.loot_modifier', env_var='FENRIL_LOOT_MODIFIER', default='shift').strip().lower()
        if loot_modifier in {'control', 'ctl'}:
            loot_modifier = 'ctrl'

        pressed_modifier = bool(loot_modifier) and loot_modifier != 'none'
        if pressed_modifier:
            utilsKeyboard.keyDown(loot_modifier)
        try:
            gameWindowSlot.rightClickSlot(
                (6, 4), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (7, 4), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (8, 4), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (6, 5), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (7, 5), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (8, 5), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (6, 6), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (7, 6), context['gameWindow']['coordinate'])
            gameWindowSlot.rightClickSlot(
                (8, 6), context['gameWindow']['coordinate'])
        finally:
            if pressed_modifier:
                utilsKeyboard.keyUp(loot_modifier)
        return context

    def onComplete(self, context: Context) -> Context:
        coordinate = context['ng_radar']['coordinate']
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 3:
            return context

        coordinates = [
            (coordinate[0] - 1, coordinate[1] - 1, coordinate[2]),
            (coordinate[0], coordinate[1] - 1, coordinate[2]),
            (coordinate[0] + 1, coordinate[1] - 1, coordinate[2]),
            (coordinate[0] - 1, coordinate[1], coordinate[2]),
            (coordinate[0], coordinate[1], coordinate[2]),
            (coordinate[0] + 1, coordinate[1], coordinate[2]),
            (coordinate[0] - 1, coordinate[1] + 1, coordinate[2]),
            (coordinate[0], coordinate[1] + 1, coordinate[2]),
            (coordinate[0] + 1, coordinate[1] + 1, coordinate[2]),
        ]

        corpses = context.get('loot', {}).get('corpsesToLoot')
        if not isinstance(corpses, list):
            return context

        new_corpses = []
        for corpse in corpses:
            if not isinstance(corpse, dict):
                continue
            corpse_coord = corpse.get('coordinate')
            if not isinstance(corpse_coord, (list, tuple)) or len(corpse_coord) < 3:
                continue
            try:
                corpse_coord_int = (int(corpse_coord[0]), int(corpse_coord[1]), int(corpse_coord[2]))
            except Exception:
                continue
            if any(coordinatesAreEqual(target, corpse_coord_int) for target in coordinates):
                continue
            new_corpses.append(corpse)

        context['loot']['corpsesToLoot'] = new_corpses

        return context
