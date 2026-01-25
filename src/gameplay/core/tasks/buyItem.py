import src.repositories.refill.core as refillCore
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.utils.console_log import log_throttled
import numpy as np


# TODO: check if item was bought checking gold difference on did
# TODO: check if has necessary money to buy item. If not, an alert to user must be sent
class BuyItemTask(BaseTask):
    def __init__(self: "BuyItemTask", itemName: str, itemQuantity: int, ignore: bool = False) -> None:
        super().__init__(delayOfTimeout=25.0)
        self.name = 'buyItem'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.timeout_config_path = 'ng_runtime.task_timeouts.buyItem'
        self.timeout_env_var = 'FENRIL_BUY_ITEM_TIMEOUT'
        self.timeout_default = 25.0
        self.shouldTimeoutTreeWhenTimeout = True
        self.itemName = itemName
        self.itemQuantity = itemQuantity
        self.ignore = ignore
        self._attempted = False

    def shouldIgnore(self, _: Context) -> bool:
        if self.ignore == True:
            return True

        return self.itemQuantity <= 0

    def do(self, context: Context) -> Context:
        screenshot = context.get('ng_screenshot')
        if screenshot is None:
            return context

        # Don't spam clicks if the trade window isn't open/visible yet.
        # Only enforce this when we have a real image array; unit tests often pass placeholders.
        if isinstance(screenshot, np.ndarray):
            try:
                if refillCore.getTradeBottomPos(screenshot) is None:
                    log_throttled(
                        'buyItem.no_trade_window',
                        'warn',
                        'buyItem: NPC trade window not detected. Ensure the trade window is visible in the capture and that the bot successfully said "hi" then "trade"/"potions".',
                        10.0,
                    )
                    return context
            except Exception:
                # If trade window detection fails for any reason, fall back to previous behavior.
                pass

        # TODO: split into multiple tasks
        refillCore.buyItem(context['ng_screenshot'],
                        self.itemName, self.itemQuantity)
        self._attempted = True
        return context

    def did(self, context: Context) -> bool:
        if self.ignore == True:
            return True
        if self.itemQuantity <= 0:
            return True
        return bool(self._attempted)
