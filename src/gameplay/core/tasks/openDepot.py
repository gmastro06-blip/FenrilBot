from src.repositories.inventory.core import images
import src.utils.core as coreUtils
import src.utils.mouse as mouse
from typing import Any, Optional, Tuple, cast
from ...typings import Context
from .common.base import BaseTask


# TODO: implement shouldIgnore method and check if depot is already open
# TODO: check if depot is opened on did
class OpenDepotTask(BaseTask):
    def __init__(self: "OpenDepotTask") -> None:
        super().__init__()
        self.name = 'openDepot'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1

    def do(self, context: Context) -> Context:
        ctx = cast(dict[str, Any], context)
        screenshot = ctx.get('ng_screenshot')
        if screenshot is None:
            return context

        depotPosition: Optional[Tuple[int, int, int, int]] = coreUtils.locate(
            screenshot,
            images['slots']['depot'],
        )
        if depotPosition is None:
            return context
        x, y, _, _ = depotPosition
        # TODO: click inside BBox
        mouse.rightClick((x + 5, y + 5))
        return context
