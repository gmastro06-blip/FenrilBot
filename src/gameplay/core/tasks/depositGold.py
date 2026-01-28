from ...typings import Context
from .common.vector import VectorTask
from .enableChat import EnableChatTask
from .say import SayTask
from .selectChatTab import SelectChatTabTask
from .setChatOff import SetChatOffTask
from .setNextWaypoint import SetNextWaypointTask
from src.utils.array import getNextArrayIndex
from src.gameplay.core.waypoint import resolveGoalCoordinate


# LIMITATION: Gold deposit validation not implemented (requires OCR).
# System assumes NPC responds to "deposit all". If NPC is unresponsive,
# task will timeout (default 25s) and skip to next waypoint.
# 
# HARDENING RECOMMENDATION: Monitor timeout frequency. High timeout rate
# indicates NPC interaction issues.
# 
# FUTURE IMPROVEMENT: Implement gold OCR
#   1. Capture gold amount before "deposit all" (getGold(screenshot))
#   2. Capture gold amount after NPC response
#   3. Validate: gold_after < gold_before (if not, deposit failed)
#   4. Retry or skip based on validation
#   See: HARDENING_RECOMMENDATIONS.md Section 1
class DepositGoldTask(VectorTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'depositGold'
        self.isRootTask = True
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1

    def onBeforeStart(self, context: Context) -> Context:
        self.tasks = [
            SelectChatTabTask('local chat').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('hi').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('deposit all').setParentTask(self).setRootTask(self),
            EnableChatTask().setParentTask(self).setRootTask(self),
            SayTask('yes').setParentTask(self).setRootTask(self),
            SetChatOffTask().setParentTask(self).setRootTask(self),
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
                context['ng_debug']['last_tick_reason'] = 'depositGold timeout (skipping)'
        except Exception:
            return context
        return context
