from typing import Any

from src.gameplay.typings import Context
from src.gameplay.utils import coordinatesAreEqual
import src.repositories.gameWindow.slot as gameWindowSlot
import src.utils.keyboard as utilsKeyboard
from .common.base import BaseTask


# TODO: check if something was looted or exactly count was looted
class CollectDeadCorpseTask(BaseTask):
    def __init__(self, creature: Any):
        super().__init__()
        self.name = 'collectDeadCorpse'
        self.delayBeforeStart = 0.85
        self.creature = creature

    def do(self, context: Context) -> Context:
        utilsKeyboard.keyDown('shift')
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
        utilsKeyboard.keyUp('shift')
        return context

    def onComplete(self, context: Context) -> Context:
        coordinate = context['ng_radar']['coordinate']
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

        context['loot']['corpsesToLoot'] = [
            corpseToLoot
            for corpseToLoot in context['loot']['corpsesToLoot']
            if not any(
                coordinatesAreEqual(target, corpseToLoot['coordinate'])
                for target in coordinates
            )
        ]

        return context
