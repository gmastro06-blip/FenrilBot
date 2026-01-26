from src.repositories.inventory.config import images
import src.repositories.inventory.core as inventoryCore
import src.utils.core as utilsCore
import src.utils.mouse as utilsMouse
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.utils.console_log import log_throttled


class OpenBackpackTask(BaseTask):
    def __init__(self: "OpenBackpackTask", backpack: str) -> None:
        super().__init__(delayOfTimeout=12.0)
        self.name = 'openBackpack'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        self.timeout_config_path = 'ng_runtime.task_timeouts.openBackpack'
        self.timeout_env_var = 'FENRIL_OPEN_BACKPACK_TIMEOUT'
        self.timeout_default = 12.0
        self.shouldTimeoutTreeWhenTimeout = True
        self.backpack = backpack

    def shouldIgnore(self, context: Context) -> bool:
        if context.get('ng_screenshot') is None:
            return False
        return inventoryCore.isContainerOpen(context['ng_screenshot'], self.backpack)

    def do(self, context: Context) -> Context:
        if context.get('ng_screenshot') is None:
            return context
        try:
            tpl = images['slots'][self.backpack]
        except Exception:
            log_throttled(
                'openBackpack.unknown_template',
                'warn',
                f"openBackpack: unknown backpack template {self.backpack!r}. Pick a backpack that exists in inventory templates.",
                10.0,
            )
            return context

        backpackPosition = utilsCore.locate(
            context['ng_screenshot'], tpl, confidence=0.8)
        if backpackPosition is None:
            backpackPosition = utilsCore.locateMultiScale(
                context['ng_screenshot'],
                tpl,
                confidence=0.78,
                scales=(0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15),
            )
        if backpackPosition is None:
            log_throttled(
                'openBackpack.not_found',
                'warn',
                f"openBackpack: couldn't locate backpack {self.backpack!r} in capture. Ensure the inventory panel (right side) is visible in OBS capture and UI scaling matches the templates.",
                10.0,
            )
            return context
        # TODO: click in random BBOX coordinate
        utilsMouse.rightClick(
            (backpackPosition[0] + 5, backpackPosition[1] + 5))
        return context

    def did(self, context: Context) -> bool:
        return self.shouldIgnore(context)
