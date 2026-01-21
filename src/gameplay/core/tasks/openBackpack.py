import os
from src.repositories.inventory.config import images
import src.repositories.inventory.core as inventoryCore
import src.utils.core as utilsCore
import src.utils.mouse as utilsMouse
from src.gameplay.typings import Context
from .common.base import BaseTask


class OpenBackpackTask(BaseTask):
    def __init__(self: "OpenBackpackTask", backpack: str) -> None:
        super().__init__()
        self.name = 'openBackpack'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.delayOfTimeout = float(os.getenv('FENRIL_OPEN_BACKPACK_TIMEOUT', '12'))
        self.shouldTimeoutTreeWhenTimeout = True
        self.backpack = backpack

    def shouldIgnore(self, context: Context) -> bool:
        if context.get('ng_screenshot') is None:
            return False
        return inventoryCore.isContainerOpen(context['ng_screenshot'], self.backpack)

    def do(self, context: Context) -> Context:
        if context.get('ng_screenshot') is None:
            return context
        backpackPosition = utilsCore.locate(
            context['ng_screenshot'], images['slots'][self.backpack], confidence=0.8)
        if backpackPosition is None:
            return context
        # TODO: click in random BBOX coordinate
        utilsMouse.rightClick(
            (backpackPosition[0] + 5, backpackPosition[1] + 5))
        return context

    def did(self, context: Context) -> bool:
        return self.shouldIgnore(context)
