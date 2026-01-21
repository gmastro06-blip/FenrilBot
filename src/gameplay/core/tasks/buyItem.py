import os
import src.repositories.refill.core as refillCore
from src.gameplay.typings import Context
from .common.base import BaseTask


# TODO: check if item was bought checking gold difference on did
# TODO: check if has necessary money to buy item. If not, an alert to user must be sent
class BuyItemTask(BaseTask):
    def __init__(self: "BuyItemTask", itemName: str, itemQuantity: int, ignore: bool = False) -> None:
        super().__init__()
        self.name = 'buyItem'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.delayOfTimeout = float(os.getenv('FENRIL_BUY_ITEM_TIMEOUT', '25'))
        self.shouldTimeoutTreeWhenTimeout = True
        self.itemName = itemName
        self.itemQuantity = itemQuantity
        self.ignore = ignore

    def shouldIgnore(self, _: Context) -> bool:
        if self.ignore == True:
            return True

        return self.itemQuantity <= 0

    def do(self, context: Context) -> Context:
        if context.get('ng_screenshot') is None:
            return context
        # TODO: split into multiple tasks
        refillCore.buyItem(context['ng_screenshot'],
                        self.itemName, self.itemQuantity)
        return context
