import src.repositories.gameWindow.core as gameWindowCore
import src.repositories.gameWindow.slot as gameWindowSlot
from src.shared.typings import Waypoint
import src.utils.keyboard as keyboard
from src.gameplay.typings import Context
from .common.base import BaseTask
from time import sleep
from src.utils.console_log import log_throttled

# HARDENING STATUS: Z-level verification implemented (2026-01-28)
# ✅ Verifies Z-level actually changed (not just hole opened)
# ✅ Retry bounded (3 attempts before force success)
# ✅ Logs clear failure reasons with coordinates
# ✅ No infinite loops possible
# 
# System is robust - matches useRope implementation pattern

class UseShovelTask(BaseTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__()
        self.name = 'useShovel'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 0.5
        self.waypoint = waypoint
        self.failedAttempts = 0  # Track failed shovel attempts

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
        # HARDENING: Verify Z-level change (expected to go down 1 level)
        current_coord = context.get('ng_radar', {}).get('coordinate')
        if current_coord is None:
            return self.shouldIgnore(context)
        
        expected_z = self.waypoint['coordinate'][2] + 1  # Shovel goes DOWN (+1 Z)
        
        if current_coord[2] != expected_z:
            # Shovel failed - increment counter
            self.failedAttempts += 1
            
            if self.failedAttempts >= 3:
                log_throttled(
                    'useShovel.failed_z_change',
                    'error',
                    f'useShovel: Failed to change Z-level after {self.failedAttempts} attempts. '
                    f'Expected Z={expected_z}, got Z={current_coord[2]}. Hole may be blocked or not diggable.',
                    10.0
                )
                # Force success to avoid infinite loop
                return True
            
            log_throttled(
                'useShovel.retry_z_change',
                'warn',
                f'useShovel: Z-level unchanged. Retry {self.failedAttempts}/3',
                5.0
            )
            return False
        
        # Success - Z-level changed
        return True
