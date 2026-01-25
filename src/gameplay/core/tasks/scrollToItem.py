from typing import Union
from src.shared.typings import BBox, GrayImage
from src.utils.core import locate
from src.utils.mouse import moveTo, scroll
from ...typings import Context
from .common.base import BaseTask


class ScrollToItemTask(BaseTask):
    def __init__(self, containerImage: GrayImage, itemImage: GrayImage):
        super().__init__(delayOfTimeout=20.0)
        self.name = 'scrollToItem'
        self.terminable = False
        self.timeout_config_path = 'ng_runtime.task_timeouts.scrollToItem'
        self.timeout_env_var = 'FENRIL_SCROLL_TO_ITEM_TIMEOUT'
        self.timeout_default = 20.0
        self.shouldTimeoutTreeWhenTimeout = True
        self.containerImage = containerImage
        self.itemImage = itemImage

    # TODO: add unit tests
    def shouldIgnore(self, context: Context) -> bool:
        if context.get('ng_screenshot') is None:
            return False
        return self.getItemPosition(context['ng_screenshot']) is not None

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        if context.get('ng_screenshot') is None:
            return context
        containerPosition = locate(context['ng_screenshot'], self.containerImage, confidence=0.8)
        if containerPosition is None:
            return context
        moveTo((containerPosition[0] + 10, containerPosition[1] + 15))
        scroll(-10)
        return context

    # TODO: add unit tests
    def ping(self, context: Context) -> Context:
        if context.get('ng_screenshot') is None:
            return context
        itemPosition = self.getItemPosition(context['ng_screenshot'])
        if itemPosition is not None:
            self.terminable = True
        return context

    # TODO: add unit tests
    def getItemPosition(self, screenshot: GrayImage) -> Union[BBox, None]:
        return locate(screenshot, self.itemImage, confidence=0.8)
