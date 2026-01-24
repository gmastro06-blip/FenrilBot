from ...typings import Context
from .common.base import BaseTask
import os
from src.utils.keyboard import keyDown, keyUp
import src.repositories.gameWindow.slot as gameWindowSlot
from src.utils.runtime_settings import get_str

class LootMonstersBoxTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'lootMonstersBox'
        self.isRootTask = True
        self.delayBeforeStart = 0.4

    def shouldIgnore(self, context: Context) -> bool:
        if context['ng_lastUsedSpellLoot'] is None:
            return True
        else:
            return False

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        loot_modifier = get_str(context, 'ng_runtime.loot_modifier', env_var='FENRIL_LOOT_MODIFIER', default='shift').strip().lower()
        if loot_modifier in {'control', 'ctl'}:
            loot_modifier = 'ctrl'

        pressed_modifier = bool(loot_modifier) and loot_modifier != 'none'
        if pressed_modifier:
            keyDown(loot_modifier)
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
                keyUp(loot_modifier)
        return context
