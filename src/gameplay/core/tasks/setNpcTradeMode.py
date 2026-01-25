from __future__ import annotations

import time
from typing import Literal

import numpy as np

import src.repositories.refill.core as refillCore
from src.repositories.refill.config import tradeTabsImages
from src.gameplay.typings import Context
from src.utils.console_log import log_throttled
from src.utils.core import locateMultiScale
from src.utils.image import crop
from src.utils.mouse import leftClick
from src.utils.runtime_settings import get_bool, get_float

from .common.base import BaseTask


TradeMode = Literal['buy', 'sell']


class SetNpcTradeModeTask(BaseTask):
    def __init__(self, mode: TradeMode) -> None:
        super().__init__()
        self.name = 'setNpcTradeMode'
        self.mode: TradeMode = mode
        self.delayBeforeStart = 0.2
        self.delayAfterComplete = 0.2
        self._attempted = False

    def do(self, context: Context) -> Context:
        # Ensure clicks land on the Tibia window (not OBS / not some overlay).
        # Default ON because trade UI clicks are otherwise easy to miss.
        try:
            if get_bool(
                context,
                'ng_runtime.focus_action_window_before_trade_clicks',
                env_var='FENRIL_FOCUS_ACTION_WINDOW_BEFORE_TRADE_CLICKS',
                default=True,
            ):
                win = context.get('action_window') or context.get('window')
                if win is not None:
                    try:
                        if hasattr(win, 'activate'):
                            win.activate()
                    except Exception:
                        pass
                    try:
                        import win32con
                        import win32gui

                        hwnd = getattr(win, '_hWnd', None)
                        if hwnd is not None:
                            if win32gui.IsIconic(hwnd):
                                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.BringWindowToTop(hwnd)
                            win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
                    try:
                        time.sleep(
                            get_float(
                                context,
                                'ng_runtime.focus_action_window_after_s',
                                env_var='FENRIL_FOCUS_ACTION_WINDOW_AFTER_S',
                                default=0.05,
                            )
                        )
                    except Exception:
                        time.sleep(0.05)
        except Exception:
            pass

        screenshot = context.get('ng_screenshot')
        if screenshot is None:
            self._attempted = True
            return context

        top = None
        try:
            top = refillCore.getTradeTopPosition(screenshot)
        except Exception:
            top = None

        if top is None:
            # If we can't detect even the top bar, avoid blind clicking.
            if isinstance(screenshot, np.ndarray):
                log_throttled(
                    'setNpcTradeMode.no_trade_window',
                    'warn',
                    'setNpcTradeMode: NPC trade window not detected; skipping mode switch.',
                    10.0,
                )
            self._attempted = True
            return context

        (x, y, tw, th) = top

        # Preferred: detect the Buy/Sell tab location via templates (robust to minor UI shifts and scaling).
        try:
            templates = tradeTabsImages.get(self.mode)
        except Exception:
            templates = None

        if templates:
            # Search only inside the trade window area to avoid false positives.
            # Older UI had a narrow trade window (~174px), but some setups (OBS/DPI or user-captured
            # trade bar templates) can report a much wider bbox. Use the detected bbox width when available.
            try:
                crop_x = int(x)
                crop_y = int(y)
                crop_w = 174
                crop_h = 120

                if isinstance(screenshot, np.ndarray):
                    max_w = int(screenshot.shape[1] - crop_x)
                    max_h = int(screenshot.shape[0] - crop_y)
                    if max_w > 0:
                        crop_w = min(max_w, max(crop_w, int(tw)))
                    if max_h > 0:
                        crop_h = min(max_h, crop_h)

                trade_window = crop(screenshot, crop_x, crop_y, crop_w, crop_h)
            except Exception:
                trade_window = None

            if isinstance(trade_window, np.ndarray):
                scales = (0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25)

                # Tabs live on the right side of the trade window.
                # Searching the entire ROI can produce false positives (small templates).
                right_x0 = 0
                try:
                    right_x0 = int(trade_window.shape[1] * 0.55)
                except Exception:
                    right_x0 = 0

                regions: list[tuple[np.ndarray, int]] = []
                if right_x0 > 0:
                    regions.append((trade_window[:, right_x0:], right_x0))
                regions.append((trade_window, 0))

                for region, xoff in regions:
                    for tpl in templates:
                        try:
                            pos = locateMultiScale(
                                region,
                                tpl,
                                confidence=0.70,
                                scales=scales,
                            )
                        except Exception:
                            pos = None

                        if pos is None:
                            continue

                        (px, py, pw, ph) = pos
                        cx = int(x) + int(xoff) + int(px) + int(pw // 2)
                        cy = int(y) + int(py) + int(ph // 2)
                        leftClick((cx, cy))
                        time.sleep(0.15)
                        self._attempted = True
                        return context

        # Fallback: Tibia trade window Buy/Sell tabs on the right side.
        # Kept for compatibility when templates are not configured.

        if self.mode == 'buy':
            click_pos = (x + 155, y + 30)
        else:
            click_pos = (x + 155, y + 52)

        leftClick(click_pos)
        time.sleep(0.15)
        self._attempted = True
        return context

    def did(self, _: Context) -> bool:
        return bool(self._attempted)
