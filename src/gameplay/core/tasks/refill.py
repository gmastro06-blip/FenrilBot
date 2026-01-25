from src.repositories.actionBar.core import getSlotCount
from src.shared.typings import Waypoint
from ...typings import Context
from .common.vector import VectorTask
from .buyItem import BuyItemTask
from .closeNpcTradeBox import CloseNpcTradeBoxTask
from .enableChat import EnableChatTask
from .expandBackpack import ExpandBackpackTask
from .openBackpack import OpenBackpackTask
from .say import SayTask
from .sellEachFlask import SellEachFlaskTask
from .selectChatTab import SelectChatTabTask
from .setNpcTradeMode import SetNpcTradeModeTask
from .setChatOff import SetChatOffTask
from .setNextWaypoint import SetNextWaypointTask
from src.gameplay.core.tasks.useHotkey import UseHotkeyTask
from src.utils.array import getNextArrayIndex
from src.gameplay.core.waypoint import resolveGoalCoordinate

class RefillTask(VectorTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__()
        self.name = 'refill'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.isRootTask = True
        self.waypoint = waypoint

    # TODO: add unit tests
    def onBeforeStart(self, context: Context) -> Context:
        screenshot = context.get('ng_screenshot') if isinstance(context, dict) else None
        if screenshot is None:
            # Capture isn't ready / window mismatch; avoid crashing and let cavebot continue.
            return self.onTimeout(context)

        health_slot = context.get('healing', {}).get('potions', {}).get('firstHealthPotion', {}).get('slot')
        mana_slot = context.get('healing', {}).get('potions', {}).get('firstManaPotion', {}).get('slot')
        if health_slot is None or mana_slot is None:
            return self.onTimeout(context)

        healthPotionsAmount = getSlotCount(screenshot, health_slot)
        manaPotionsAmount = getSlotCount(screenshot, mana_slot)
        if healthPotionsAmount is None or manaPotionsAmount is None:
            return self.onTimeout(context)

        amountOfManaPotionsToBuy = max(
            0, self.waypoint['options']['manaPotion']['quantity'] - manaPotionsAmount)
        amountOfHealthPotionsToBuy = max(
            0, self.waypoint['options']['healthPotion']['quantity'] - healthPotionsAmount)

        # Optional: sell empty containers before buying potions.
        # Defaults to True (safe allow-list) and can be disabled per waypoint.
        sell_before_refill = True
        sellable_items = ['empty potion flask', 'empty vial']
        amount_per_stack = 100
        max_slots_to_scan = 400
        max_no_trade_retries = 10
        max_no_screenshot_retries = 10
        max_consecutive_unknown_slots = 12

        try:
            opts = self.waypoint.get('options') if isinstance(self.waypoint, dict) else None
            if isinstance(opts, dict):
                sbr = opts.get('sellFlasksBeforeRefill')
                if isinstance(sbr, bool):
                    sell_before_refill = sbr

                si = opts.get('sellableItems')
                if isinstance(si, list) and all(isinstance(x, str) for x in si):
                    sellable_items = [x for x in si if x]

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
        except Exception:
            pass

        main_backpack = None
        try:
            if isinstance(context.get('ng_backpacks'), dict):
                main_backpack = context['ng_backpacks'].get('main')
        except Exception:
            main_backpack = None

        sell_tasks = []
        if sell_before_refill and isinstance(main_backpack, str) and main_backpack:
            sell_tasks = [
                SetNpcTradeModeTask('sell').setParentTask(self).setRootTask(self),
                OpenBackpackTask(main_backpack).setParentTask(self).setRootTask(self),
                ExpandBackpackTask(main_backpack).setParentTask(self).setRootTask(self),
                SellEachFlaskTask(
                    main_backpack,
                    amount_per_stack=amount_per_stack,
                    sellable_items=sellable_items,
                    max_slots_to_scan=max_slots_to_scan,
                    max_no_trade_window_ticks=max_no_trade_retries,
                    max_no_screenshot_ticks=max_no_screenshot_retries,
                    max_consecutive_unknown_slots=max_consecutive_unknown_slots,
                ).setParentTask(self).setRootTask(self),
            ]

        self.tasks = [
            SelectChatTabTask('local chat').setParentTask(
                self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('hi').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('potions' if self.waypoint['options']['houseNpcEnabled'] else 'trade').setParentTask(self).setRootTask(self),
            SetChatOffTask().setParentTask(self).setRootTask(self),
            *sell_tasks,
            SetNpcTradeModeTask('buy').setParentTask(self).setRootTask(self),
            BuyItemTask(self.waypoint['options']['manaPotion']['item'], amountOfManaPotionsToBuy).setParentTask(
                self).setRootTask(self),
            BuyItemTask(self.waypoint['options']['healthPotion']['item'], amountOfHealthPotionsToBuy, ignore=not self.waypoint['options']['healthPotionEnabled']).setParentTask(
                self).setRootTask(self),
            CloseNpcTradeBoxTask().setParentTask(self).setRootTask(self),
            UseHotkeyTask(context['healing']['potions']['firstManaPotion']['hotkey'], delayAfterComplete=1).setParentTask(self).setRootTask(self),
            SetNextWaypointTask().setParentTask(self).setRootTask(self),
        ]
        return context

    def onTimeout(self, context: Context) -> Context:
        try:
            items = context.get('ng_cave', {}).get('waypoints', {}).get('items')
            current_idx = context.get('ng_cave', {}).get('waypoints', {}).get('currentIndex')
            coord = context.get('ng_radar', {}).get('coordinate')
            if not items or current_idx is None:
                return context
            next_idx = getNextArrayIndex(items, current_idx)
            context['ng_cave']['waypoints']['currentIndex'] = next_idx
            if coord is not None:
                current_wp = items[next_idx]
                context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(coord, current_wp)
            if isinstance(context.get('ng_debug'), dict):
                context['ng_debug']['last_tick_reason'] = 'refill timeout (skipping)'
        except Exception:
            return context
        return context
