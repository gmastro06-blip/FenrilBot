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
        if not self.backpack:
            return context

        # If it's already open, nothing to do (also avoids requiring a slots icon template).
        if inventoryCore.isContainerOpen(context['ng_screenshot'], self.backpack):
            return context

        # Support template variants without changing configured backpack names.
        # Example: user can add `Camouflage Backpack v2.png` to slots/ and it will be tried too.
        candidate_keys = [self.backpack]
        try:
            candidate_keys.extend(
                [
                    k
                    for k in images.get('slots', {}).keys()
                    if isinstance(k, str) and k != self.backpack and k.startswith(self.backpack + ' ')
                ]
            )
        except Exception:
            pass

        templates = []
        for k in candidate_keys:
            try:
                templates.append(images['slots'][k])
            except Exception:
                continue

        if not templates:
            log_throttled(
                'openBackpack.unknown_template',
                'warn',
                f"openBackpack: missing slots icon template for {self.backpack!r}. If the backpack is already open, this is fine; otherwise add a slots template (e.g. 'slots/{self.backpack} v2.png').",
                10.0,
            )
            return context

        backpackPosition = None
        for tpl in templates:
            backpackPosition = utilsCore.locate(context['ng_screenshot'], tpl, confidence=0.8)
            if backpackPosition is None:
                backpackPosition = utilsCore.locateMultiScale(
                    context['ng_screenshot'],
                    tpl,
                    confidence=0.78,
                    scales=(0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30),
                )
            if backpackPosition is not None:
                break

        if backpackPosition is None:
            # If the container is already open, treat as success (no need to click the icon).
            if inventoryCore.isContainerOpen(context['ng_screenshot'], self.backpack):
                return context
            log_throttled(
                'openBackpack.not_found',
                'warn',
                f"openBackpack: couldn't locate backpack {self.backpack!r} in capture. Ensure the inventory panel / container with the backpack icon is visible and UI scaling matches the templates.",
                10.0,
            )
            return context
        # TODO: click in random BBOX coordinate
        utilsMouse.rightClick(
            (backpackPosition[0] + 5, backpackPosition[1] + 5))
        return context

    def did(self, context: Context) -> bool:
        return self.shouldIgnore(context)
