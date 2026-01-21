"""One-off diagnostic: locate and click a battle list entry.

Usage (PowerShell):
  $env:FENRIL_CAPTURE_WINDOW_TITLE='Proyector en ventana (Fuente) - Tibia_Fuente'
  $env:FENRIL_ACTION_WINDOW_TITLE='Tibia - ...'   # optional
  $env:FENRIL_DISABLE_ARDUINO='1'                 # recommended for fast clicks
  $env:FENRIL_BATTLELIST_CLICK_INDEX='0'
  $env:FENRIL_BATTLELIST_CLICK_X_OFFSET='60'      # optional
    ./.venv/Scripts/python.exe -u scripts/test_battlelist_click.py

It will:
- resolve capture/action windows
- take screenshots until the battle list click coordinate is found
- dump a debug screenshot
- click once (left click by default)
"""

from __future__ import annotations

import os
import pathlib
import sys
import time
from typing import Optional, cast

import cv2
import numpy as np

# Allow running this file directly (adds repo root so `import src.*` works).
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gameplay.context import context as base_context
from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware
from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.repositories.battleList import extractors as battlelist_extractors
import src.utils.mouse as mouse


def _focus_action_window(ctx: dict) -> bool:
    if os.getenv('FENRIL_FOCUS_ACTION_WINDOW', '1') in {'0', 'false', 'False'}:
        return False

    win = ctx.get('action_window') or ctx.get('window')
    if win is None:
        return False

    focused = False
    try:
        if hasattr(win, 'activate'):
            win.activate()
            focused = True
    except Exception:
        pass

    try:
        import win32con
        import win32gui

        hwnd = getattr(win, '_hWnd', None)
        if hwnd is not None:
            try:
                    # SW_RESTORE un-maximizes if the window is maximized.
                    # Only restore when minimized.
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception:
                pass
            try:
                win32gui.BringWindowToTop(hwnd)
            except Exception:
                pass
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            focused = True
    except Exception:
        pass

    if focused:
        try:
            time.sleep(float(os.getenv('FENRIL_FOCUS_AFTER_S', '0.10')))
        except Exception:
            time.sleep(0.10)
    return focused


def main() -> int:
    ctx = dict(base_context)
    ctx['ng_pause'] = False
    ctx['ng_debug'] = {'last_tick_reason': None}
    ctx['ng_diag'] = {}

    out_dir = pathlib.Path('debug')
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = int(os.getenv('FENRIL_BATTLELIST_CLICK_INDEX', '0'))
    button = os.getenv('FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON', 'left').strip().lower()
    if button not in {'left', 'right'}:
        button = 'left'

    deadline = time.time() + float(os.getenv('FENRIL_TEST_CLICK_TIMEOUT_S', '10.0'))
    attempt = 0
    shot_none_count = 0
    last_shot: Optional[np.ndarray] = None

    while time.time() < deadline:
        attempt += 1
        ctx = setTibiaWindowMiddleware(ctx)
        ctx = setScreenshotMiddleware(ctx)
        shot = ctx.get('ng_screenshot')
        if shot is None:
            shot_none_count += 1
            time.sleep(0.05)
            continue

        # Typing: `ng_screenshot` is a numpy array (OpenCV image).
        shot_np = cast(np.ndarray, shot)
        last_shot = shot_np

        click = battlelist_extractors.getCreatureClickCoordinate(shot_np, index=idx)
        if click is None:
            if attempt % 10 == 0:
                print(f"[test] attempt={attempt}: battle list click coord not found yet")
            time.sleep(0.05)
            continue

        ts = int(time.time() * 1000)
        dump_path = out_dir / f"test_battlelist_click_{ts}.png"
        try:
            cv2.imwrite(str(dump_path), np.ascontiguousarray(shot_np))
        except Exception:
            pass

        abs_click = mouse.transform_capture_to_action(click)
        cap_rect, act_rect = mouse.get_window_transform()
        focused = _focus_action_window(ctx)
        print(f"[test] FOUND click={click} abs={abs_click} cap_rect={cap_rect} act_rect={act_rect} idx={idx} button={button}")
        print(f"[test] focus_action_window={focused}")
        print(f"[test] dumped screenshot: {dump_path}")

        click_at_cursor = os.getenv('FENRIL_TEST_CLICK_AT_CURSOR', '0') in {'1', 'true', 'True'}
        if click_at_cursor:
            mouse.moveTo(click)
            time.sleep(float(os.getenv('FENRIL_TEST_CLICK_PRE_DELAY_S', '0.15')))
            if button == 'right':
                mouse.rightClick(None)
            else:
                mouse.leftClick(None)
        else:
            # Prefer coordinate-based click (more reliable if Arduino movement is delayed).
            if button == 'right':
                mouse.rightClick(click)
            else:
                mouse.leftClick(click)
        print(f"[test] click sent backend={mouse.get_last_click_backend()!r}")
        return 0

    if last_shot is not None:
        ts = int(time.time() * 1000)
        dump_path = out_dir / f"test_battlelist_click_timeout_{ts}.png"
        try:
            cv2.imwrite(str(dump_path), np.ascontiguousarray(last_shot))
            print(f"[test] dumped last screenshot on timeout: {dump_path}")
        except Exception:
            pass

    print(f"[test] timeout: could not locate battle list click coordinate (shot_none={shot_none_count})")
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
