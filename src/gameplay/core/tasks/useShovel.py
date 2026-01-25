import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
from src.shared.typings import Waypoint
import src.utils.keyboard as keyboard
from src.gameplay.typings import Context
from .common.base import BaseTask
from time import sleep
from src.utils.console_log import log_throttled

class UseShovelTask(BaseTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__()
        self.name = 'useShovel'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 0.5
        self.waypoint = waypoint

    def shouldIgnore(self, context: Context) -> bool:
        return gameWindowCore.isHoleOpen(
            context['gameWindow']['image'], gameWindowCore.images[context['ng_resolution']]['holeOpen'], context['ng_radar']['coordinate'], self.waypoint['coordinate'])

    def do(self, context: Context) -> Context:
        slot = gameWindowCore.getSlotFromCoordinate(
            context['ng_radar']['coordinate'], self.waypoint['coordinate'])
        if slot is None:
            return context
        sleep(0.2)
        shovel_hotkey = None
        try:
            shovel_hotkey = context.get('general_hotkeys', {}).get('shovel_hotkey')
        except Exception:
            shovel_hotkey = None
        if isinstance(shovel_hotkey, str):
            shovel_hotkey = shovel_hotkey.strip()
        if not shovel_hotkey:
            shovel_hotkey = 'p'
            log_throttled(
                'useShovel.default_hotkey',
                'warn',
                "useShovel: general_hotkeys.shovel_hotkey not set; falling back to 'p'.",
                30.0,
            )
        keyboard.press(shovel_hotkey)
        sleep(0.2)
        gameWindowSlot.clickSlot(slot, context['gameWindow']['coordinate'])
        sleep(0.2)
        return context

    def did(self, context: Context) -> bool:
        return self.shouldIgnore(context)
