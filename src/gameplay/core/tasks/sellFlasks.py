from src.shared.typings import Waypoint

from ...typings import Context
from .common.vector import VectorTask
from .closeNpcTradeBox import CloseNpcTradeBoxTask
from .enableChat import EnableChatTask
from .openBackpack import OpenBackpackTask
from .expandBackpack import ExpandBackpackTask
from .say import SayTask
from .selectChatTab import SelectChatTabTask
from .sellEachFlask import SellEachFlaskTask
from .setChatOff import SetChatOffTask
from .setNextWaypoint import SetNextWaypointTask


class SellFlasksTask(VectorTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__()
        self.name = 'sellFlasks'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.isRootTask = True
        self.waypoint = waypoint

    def onBeforeStart(self, context: Context) -> Context:
        amount_per_stack = 100
        max_slots_to_scan = 400
        max_no_trade_retries = 10
        max_no_screenshot_retries = 10
        max_consecutive_unknown_slots = 12
        sellable_items = ['empty potion flask', 'empty vial']
        try:
            opts = self.waypoint.get('options') if isinstance(self.waypoint, dict) else None
            if isinstance(opts, dict):
                aps = opts.get('amountPerStack')
                if isinstance(aps, int):
                    amount_per_stack = max(1, aps)

                msts = opts.get('maxSlotsToScan')
                if isinstance(msts, int):
                    max_slots_to_scan = max(1, msts)

                mntr = opts.get('maxNoTradeRetries')
                if isinstance(mntr, int):
                    max_no_trade_retries = max(1, mntr)

                mnsr = opts.get('maxNoScreenshotRetries')
                if isinstance(mnsr, int):
                    max_no_screenshot_retries = max(1, mnsr)

                mcus = opts.get('maxConsecutiveUnknownSlots')
                if isinstance(mcus, int):
                    max_consecutive_unknown_slots = max(1, mcus)

                si = opts.get('sellableItems')
                if isinstance(si, list) and all(isinstance(x, str) for x in si):
                    sellable_items = [x for x in si if x]
        except Exception:
            pass

        self.tasks = [
            SelectChatTabTask('local chat').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('hi').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('trade').setParentTask(self).setRootTask(self),
            SetChatOffTask().setParentTask(self).setRootTask(self),
            OpenBackpackTask(context['ng_backpacks']['main']).setParentTask(self).setRootTask(self),
            ExpandBackpackTask(context['ng_backpacks']['main']).setParentTask(self).setRootTask(self),
            SellEachFlaskTask(
                context['ng_backpacks']['main'],
                amount_per_stack=amount_per_stack,
                sellable_items=sellable_items,
                max_slots_to_scan=max_slots_to_scan,
                max_no_trade_window_ticks=max_no_trade_retries,
                max_no_screenshot_ticks=max_no_screenshot_retries,
                max_consecutive_unknown_slots=max_consecutive_unknown_slots,
            ).setParentTask(self).setRootTask(self),
            CloseNpcTradeBoxTask().setParentTask(self).setRootTask(self),
            SetNextWaypointTask().setParentTask(self).setRootTask(self),
        ]
        return context
