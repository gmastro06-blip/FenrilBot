import time
from typing import Iterable, Optional, Tuple

import numpy as np
import src.repositories.refill.core as refillCore
from src.repositories.gameWindow.slot import getSlotPosition
from src.repositories.inventory.config import slotsImagesHashes
from src.repositories.inventory.core import images
from src.utils.console_log import log_throttled
from src.utils.core import hashit, locate
from src.utils.mouse import drag

from ...typings import Context
from .common.base import BaseTask


class SellEachFlaskTask(BaseTask):
    def __init__(
        self: "SellEachFlaskTask",
        backpack: str,
        amount_per_stack: int = 100,
        *,
        sellable_items: Optional[Iterable[str]] = None,
        max_slots_to_scan: int = 400,
        max_no_trade_window_ticks: int = 10,
        max_no_screenshot_ticks: int = 10,
        max_consecutive_unknown_slots: int = 12,
    ) -> None:
        super().__init__()
        self.name = 'sellEachFlask'
        self.delayOfTimeout = 1
        self.terminable = False
        self.slotIndex = 0
        self.backpack = backpack
        self.amount_per_stack = amount_per_stack
        if sellable_items is None:
            self._sellable_items = {'empty potion flask', 'empty vial'}
        else:
            self._sellable_items = {str(x) for x in sellable_items if x is not None}
        self._no_screenshot_ticks = 0
        self._no_trade_window_ticks = 0
        self._consecutive_unknown_slots = 0
        self._max_slots_to_scan = max(1, int(max_slots_to_scan))
        self._max_no_trade_window_ticks = max(1, int(max_no_trade_window_ticks))
        self._max_no_screenshot_ticks = max(1, int(max_no_screenshot_ticks))
        self._max_consecutive_unknown_slots = max(1, int(max_consecutive_unknown_slots))

    def do(self, context: Context) -> Context:
        screenshot = context.get('ng_screenshot')
        if screenshot is None:
            self._no_screenshot_ticks += 1
            if self._no_screenshot_ticks >= self._max_no_screenshot_ticks:
                log_throttled(
                    'sellEachFlask.no_screenshot',
                    'warn',
                    'sellEachFlask: No screenshot in context; skipping sell to avoid stalling.',
                    10.0,
                )
                self.terminable = True
            return context

        self._no_screenshot_ticks = 0

        if self.slotIndex >= self._max_slots_to_scan:
            log_throttled(
                'sellEachFlask.max_slots_reached',
                'warn',
                f'sellEachFlask: Reached max slots to scan ({self._max_slots_to_scan}); skipping remaining slots to avoid stalling.',
                10.0,
            )
            self.terminable = True
            return context

        tradeBottomPos = None
        if isinstance(screenshot, np.ndarray):
            try:
                tradeBottomPos = refillCore.getTradeBottomPos(screenshot)
                if tradeBottomPos is None:
                    self._no_trade_window_ticks += 1
                    log_throttled(
                        'sellEachFlask.no_trade_window',
                        'warn',
                        'sellEachFlask: NPC trade window not detected. Ensure the bot is at the NPC and that "hi" then "trade" succeeded.',
                        10.0,
                    )
                    if self._no_trade_window_ticks >= self._max_no_trade_window_ticks:
                        log_throttled(
                            'sellEachFlask.no_trade_window_skip',
                            'warn',
                            'sellEachFlask: Trade window still not detected after retries; skipping sell to avoid stalling.',
                            10.0,
                        )
                        self.terminable = True
                    return context
                self._no_trade_window_ticks = 0
            except Exception:
                pass

        (item, position) = self.getSlot(context, self.slotIndex)
        if item is None:
            self._consecutive_unknown_slots += 1
            if self._consecutive_unknown_slots >= self._max_consecutive_unknown_slots:
                log_throttled(
                    'sellEachFlask.unknown_slots_skip',
                    'warn',
                    'sellEachFlask: Too many consecutive unrecognized slots; skipping sell to avoid stalling (missing inventory hashes or full backpack).',
                    10.0,
                )
                self.terminable = True
                return context
            self.slotIndex += 1
            return context
        if item == 'empty slot':
            self.terminable = True
            return context

        self._consecutive_unknown_slots = 0

        # Only sell allowed empty containers (strict allow-list).
        if item not in self._sellable_items:
            self.slotIndex += 1
            return context

        if tradeBottomPos is None:
            try:
                tradeBottomPos = refillCore.getTradeBottomPos(screenshot)
            except Exception:
                tradeBottomPos = None
        if tradeBottomPos is None:
            self._no_trade_window_ticks += 1
            if self._no_trade_window_ticks >= self._max_no_trade_window_ticks:
                log_throttled(
                    'sellEachFlask.no_trade_window_skip2',
                    'warn',
                    'sellEachFlask: Trade window not detected during sell; skipping to avoid stalling.',
                    10.0,
                )
                self.terminable = True
            return context

        tradeTopPos = None
        try:
            tradeTopPos = refillCore.getTradeTopPosition(screenshot)
        except Exception:
            tradeTopPos = None

        (bx, by, _, _) = tradeBottomPos
        # Best-effort: drop into the trade item list area.
        # Prefer anchoring to the detected trade top bar when available.
        if tradeTopPos is not None:
            (tx, ty, _, _) = tradeTopPos
            drop_target = (tx + 60, ty + 70)
        else:
            drop_target = (bx + 40, max(0, by - 140))

        drag((position[0], position[1]), drop_target)
        time.sleep(0.35)

        # Many clients prompt for amount when selling stackables.
        # Using a high number is fine; the client caps to the stack size.
        refillCore.setAmount(screenshot, max(1, int(self.amount_per_stack)))
        time.sleep(0.25)
        refillCore.confirmBuyItem(screenshot)
        time.sleep(0.35)
        try:
            refillCore.clearSearchBox(screenshot)
        except Exception:
            pass
        time.sleep(0.2)

        self.slotIndex += 1
        return context

    def did(self, _: Context) -> bool:
        return bool(self.terminable)

    def getSlot(self, context: Context, slotIndex: int) -> Tuple[Optional[str], Tuple[int, int]]:
        backpackBarPosition = locate(context['ng_screenshot'], images['containersBars'][self.backpack], confidence=0.8)
        if backpackBarPosition is None:
            return (None, (0, 0))
        slotXIndex = slotIndex % 4
        slotYIndex = slotIndex // 4
        containerPositionX, containerPositionY = backpackBarPosition[1] + 18, backpackBarPosition[0] + 10
        y0 = containerPositionX + slotYIndex * 32 + slotYIndex * 5
        y1 = y0 + 21
        x0 = containerPositionY + slotXIndex * 32 + slotXIndex * 5
        x1 = x0 + 32
        firstSlotImage = context['ng_screenshot'][y0:y1, x0:x1]
        firstSlotImageHash = hashit(firstSlotImage)
        item = slotsImagesHashes.get(firstSlotImageHash, None)
        return (item, (x0 + 16, y0 + 16))
