from src.repositories.actionBar.core import getSlotCount
from src.shared.typings import Waypoint
from ...typings import Context
from .common.vector import VectorTask
from .buyItem import BuyItemTask
from .closeNpcTradeBox import CloseNpcTradeBoxTask
from .enableChat import EnableChatTask
from .say import SayTask
from .selectChatTab import SelectChatTabTask
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
        self.tasks = [
            SelectChatTabTask('local chat').setParentTask(
                self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('hi').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('potions' if self.waypoint['options']['houseNpcEnabled'] else 'trade').setParentTask(self).setRootTask(self),
            SetChatOffTask().setParentTask(self).setRootTask(self),
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
