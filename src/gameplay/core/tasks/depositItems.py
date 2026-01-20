from src.repositories.inventory.core import images
from src.shared.typings import Waypoint
from src.gameplay.typings import Context
from .common.vector import VectorTask
from .closeContainer import CloseContainerTask
from .dragItems import DragItemsTask
from .dropBackpackIntoStash import DropBackpackIntoStashTask
from .goToFreeDepot import GoToFreeDepotTask
from .openBackpack import OpenBackpackTask
from .openDepot import OpenDepotTask
from .openLocker import OpenLockerTask
from .scrollToItem import ScrollToItemTask
from .setNextWaypoint import SetNextWaypointTask
from src.utils.array import getNextArrayIndex
from src.gameplay.core.waypoint import resolveGoalCoordinate

class DepositItemsTask(VectorTask):
    def __init__(self: "DepositItemsTask", waypoint: Waypoint) -> None:
        super().__init__()
        self.name = 'depositItems'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.isRootTask = True
        self.waypoint = waypoint

    def onBeforeStart(self, context: Context) -> Context:
        self.tasks = [
            GoToFreeDepotTask(self.waypoint).setParentTask(self).setRootTask(self),
            OpenLockerTask().setParentTask(self).setRootTask(self),
            OpenBackpackTask(context['ng_backpacks']['main']).setParentTask(self).setRootTask(self),
            ScrollToItemTask(images['containersBars'][context['ng_backpacks']['main']], images['slots'][context['ng_backpacks']['loot']]).setParentTask(self).setRootTask(self),
            DropBackpackIntoStashTask(context['ng_backpacks']['loot']).setParentTask(self).setRootTask(self),
            OpenDepotTask().setParentTask(self).setRootTask(self),
            OpenBackpackTask(context['ng_backpacks']['loot']).setParentTask(self).setRootTask(self),
            DragItemsTask(images['containersBars'][context['ng_backpacks']['loot']], images['slots']['depot chest 2']).setParentTask(self).setRootTask(self),
            CloseContainerTask(images['containersBars'][context['ng_backpacks']['loot']]).setParentTask(self).setRootTask(self),
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
                context['ng_debug']['last_tick_reason'] = 'depositItems timeout (skipping)'
        except Exception:
            return context
        return context
