import os
from typing import Optional, cast

from src.repositories.inventory.core import images
import src.utils.core as coreUtils
import src.utils.mouse as mouseUtils
from ...typings import Context
from .common.base import BaseTask


# TODO: by cap, is possible to detect if task was did. But it can happen that the backpack is empty.
class DropBackpackIntoStashTask(BaseTask):
    def __init__(self: "DropBackpackIntoStashTask", backpack: str) -> None:
        super().__init__()
        self.name = 'dropBackpackIntoStash'
        self.delayAfterComplete = 1
        self.delayOfTimeout = float(os.getenv('FENRIL_DROP_BACKPACK_INTO_STASH_TIMEOUT', '20'))
        # If we can't stash the backpack, abort the whole deposit tree.
        self.shouldTimeoutTreeWhenTimeout = True
        self.terminable = False
        self.backpack = backpack
        self._did_drag_once = False

    def shouldIgnore(self, context: Context) -> bool:
        screenshot = context.get('ng_screenshot') if isinstance(context, dict) else None
        if screenshot is None:
            return False
        stash_pos = coreUtils.locate(screenshot, images['slots']['stash'])
        if stash_pos is None:
            return False
        return coreUtils.locate(screenshot, images['slots'][self.backpack], confidence=0.8) is None

    def do(self, context: Context) -> Context:
        screenshot = context.get('ng_screenshot') if isinstance(context, dict) else None
        if screenshot is None:
            return context
        backpackPosition: Optional[tuple[int, int, int, int]] = coreUtils.locate(
            screenshot, images['slots'][self.backpack], confidence=0.8)
        stashPosition: Optional[tuple[int, int, int, int]] = coreUtils.locate(
            screenshot, images['slots']['stash'])
        if backpackPosition is None or stashPosition is None:
            return context
        backpackPosition = cast(tuple[int, int, int, int], backpackPosition)
        stashPosition = cast(tuple[int, int, int, int], stashPosition)
        mouseUtils.drag(
            (backpackPosition[0] + 2, backpackPosition[1] + 2),
            (stashPosition[0] + 2, stashPosition[1] + 2),
        )
        self._did_drag_once = True
        return context

    def ping(self, context: Context) -> Context:
        if self.shouldIgnore(context):
            self.terminable = True
        return context

    def did(self, context: Context) -> bool:
        # Only declare success after the stash is visible and the backpack is no longer detected.
        return self._did_drag_once and self.shouldIgnore(context)
