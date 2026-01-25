from src.repositories.inventory.core import images
import src.utils.core as coreUtils
import src.utils.mouse as mouse
from typing import Any, Optional, Tuple, cast
from ...typings import Context
from .common.base import BaseTask
from src.utils.runtime_settings import get_str
from src.utils.console_log import log_throttled


class OpenDepotTask(BaseTask):
    def __init__(self: "OpenDepotTask") -> None:
        super().__init__(delayOfTimeout=10.0)
        self.name = 'openDepot'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.timeout_config_path = 'ng_runtime.task_timeouts.openDepot'
        self.timeout_env_var = 'FENRIL_OPEN_DEPOT_TIMEOUT'
        self.timeout_default = 10.0
        # If we can't open the depot, abort the whole deposit tree (DepositItemsTask has onTimeout skip logic).
        self.shouldTimeoutTreeWhenTimeout = True

    def shouldIgnore(self, context: Context) -> bool:
        # Consider depot "open" when any depot chest slot is visible.
        screenshot = context.get('ng_screenshot') if isinstance(context, dict) else None
        if screenshot is None:
            return False
        for key in ('depot chest 1', 'depot chest 2', 'depot chest 3', 'depot chest 4'):
            try:
                if coreUtils.locate(screenshot, images['slots'][key]) is not None:
                    return True
            except Exception:
                continue
        return False

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
            btn = get_str(ctx, 'ng_runtime.depot_open_button', env_var='FENRIL_DEPOT_OPEN_BUTTON', default='right').strip().lower()
            log_throttled(
                'openDepot.no_icon',
                'warn',
                f"openDepot: depot icon not found in capture (locker open? UI visible?). Current depot_open_button={btn!r}.",
                10.0,
            )
            return context
        x, y, w, h = depotPosition
        # Click near the center to avoid missing the depot icon.
        cx = int(x + max(1, w // 2))
        cy = int(y + max(1, h // 2))
        button = get_str(ctx, 'ng_runtime.depot_open_button', env_var='FENRIL_DEPOT_OPEN_BUTTON', default='right').strip().lower()
        if button == 'left':
            mouse.leftClick((cx, cy))
        else:
            mouse.rightClick((cx, cy))
        return context

    def did(self, context: Context) -> bool:
        return self.shouldIgnore(context)
