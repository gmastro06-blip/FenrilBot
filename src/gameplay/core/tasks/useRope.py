import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
from src.shared.typings import Waypoint
import src.utils.keyboard as keyboard
from src.gameplay.typings import Context
from .common.base import BaseTask
from time import sleep
from src.utils.console_log import log_throttled

class UseRopeTask(BaseTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__()
        self.name = 'useRope'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 1
        # If the rope doesn't change floors, abort the whole waypoint task.
        self.shouldTimeoutTreeWhenTimeout = True

        # Runtime-configurable timeout.
        self.timeout_config_path = 'ng_runtime.task_timeouts.useRope'
        self.timeout_env_var = 'FENRIL_TIMEOUT_USE_ROPE'
        self.timeout_default = 6.0

        self.waypoint = waypoint

    def do(self, context: Context) -> Context:
        slot = gameWindowCore.getSlotFromCoordinate(
            context['ng_radar']['coordinate'], self.waypoint['coordinate'])
        if slot is None:
            return context
        sleep(0.2)
        rope_hotkey = None
        try:
            rope_hotkey = context.get('general_hotkeys', {}).get('rope_hotkey')
        except Exception:
            rope_hotkey = None
        if isinstance(rope_hotkey, str):
            rope_hotkey = rope_hotkey.strip()
        if not rope_hotkey:
            rope_hotkey = 'o'
            log_throttled(
                'useRope.default_hotkey',
                'warn',
                "useRope: general_hotkeys.rope_hotkey not set; falling back to 'o'.",
                30.0,
            )
        keyboard.press(rope_hotkey)
        sleep(0.2)
        gameWindowSlot.clickSlot(slot, context['gameWindow']['coordinate'])
        sleep(0.2)
        return context

    def did(self, context: Context) -> bool:
        coord = context.get('ng_radar', {}).get('coordinate')
        target = self.waypoint.get('coordinate') if isinstance(self.waypoint, dict) else None
        if coord is None or target is None:
            return False
        # Success: after using rope on a tile at Z, we should be at Z-1.
        try:
            return int(coord[2]) == int(target[2]) - 1
        except Exception:
            return False
