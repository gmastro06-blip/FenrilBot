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
from src.utils.console_log import log_throttled
from src.utils.runtime_settings import get_bool

class DepositItemsTask(VectorTask):
    def __init__(self: "DepositItemsTask", waypoint: Waypoint) -> None:
        super().__init__()
        self.name = 'depositItems'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.isRootTask = True
        self.waypoint = waypoint

    def onBeforeStart(self, context: Context) -> Context:
        # Validate backpack config early; otherwise the task can stall on openBackpack forever
        # when the capture doesn't include the inventory panel or when names are missing.
        try:
            bp = context.get('ng_backpacks', {}) if isinstance(context, dict) else {}
            main_bp = (bp.get('main') or '').strip() if isinstance(bp, dict) else ''
            loot_bp = (bp.get('loot') or '').strip() if isinstance(bp, dict) else ''
        except Exception:
            main_bp, loot_bp = '', ''

        if not main_bp or not loot_bp:
            log_throttled(
                'depositItems.missing_backpacks',
                'warn',
                'depositItems: missing ng_backpacks.main/ng_backpacks.loot configuration. Set your Main/Loot backpacks in the UI before using depositItems.',
                10.0,
            )
            return self.onTimeout(context)

        try:
            # Ensure the required templates exist.
            _ = images['containersBars'][main_bp]
            _ = images['containersBars'][loot_bp]
            _ = images['slots'][main_bp]
            _ = images['slots'][loot_bp]
        except Exception:
            log_throttled(
                'depositItems.unknown_backpacks',
                'warn',
                f"depositItems: backpack templates not found for main={main_bp!r} loot={loot_bp!r}. Pick backpacks that exist in inventory templates.",
                10.0,
            )
            return self.onTimeout(context)

        self.tasks = [
            GoToFreeDepotTask(self.waypoint).setParentTask(self).setRootTask(self),
            OpenLockerTask().setParentTask(self).setRootTask(self),
            OpenBackpackTask(main_bp).setParentTask(self).setRootTask(self),
            ScrollToItemTask(images['containersBars'][main_bp], images['slots'][loot_bp]).setParentTask(self).setRootTask(self),
            DropBackpackIntoStashTask(loot_bp).setParentTask(self).setRootTask(self),
            OpenDepotTask().setParentTask(self).setRootTask(self),
            OpenBackpackTask(loot_bp).setParentTask(self).setRootTask(self),
            DragItemsTask(images['containersBars'][loot_bp], images['slots']['depot chest 2']).setParentTask(self).setRootTask(self),
            CloseContainerTask(images['containersBars'][loot_bp]).setParentTask(self).setRootTask(self),
            SetNextWaypointTask().setParentTask(self).setRootTask(self),
        ]

        # If radar is currently unavailable, GoToFreeDepot cannot navigate.
        # Allow an opt-in shortcut to run the depot sequence directly when the player is
        # already standing at the depot (common during supervised testing).
        try:
            coord = context.get('ng_radar', {}).get('coordinate')
            coord_missing = coord is None or (isinstance(coord, (list, tuple)) and any(c is None for c in coord))
        except Exception:
            coord_missing = True

        if coord_missing and get_bool(
            context,
            'ng_runtime.deposit_skip_goto_when_no_coord',
            env_var='FENRIL_DEPOSIT_SKIP_GOTO_WHEN_NO_COORD',
            default=False,
        ):
            log_throttled(
                'depositItems.skip_goto_no_coord',
                'warn',
                'depositItems: coord is missing; skipping goToFreeDepot (running depot open/deposit sequence directly).',
                10.0,
            )
            self.tasks = [t for t in self.tasks if getattr(t, 'name', None) != 'goToFreeDepot']
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
