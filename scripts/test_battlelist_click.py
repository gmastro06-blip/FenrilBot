"""One-off diagnostic: locate and click a battle list entry.

Usage (PowerShell):
    ./.venv/Scripts/python.exe -u scripts/test_battlelist_click.py --index 0 --button left --timeout-s 10

Optional env vars are still supported for convenience, but not required.

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
import argparse
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


def _focus_action_window(ctx: dict, *, enabled: bool, focus_after_s: float) -> bool:
    if not enabled:
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
        time.sleep(max(0.0, float(focus_after_s)))
    return focused


def main() -> int:
    parser = argparse.ArgumentParser(description='One-off diagnostic: locate and click a battle list entry')
    parser.add_argument('--index', type=int, default=None, help='Battlelist entry index (default: 0)')
    parser.add_argument('--button', type=str, default=None, choices=['left', 'right'], help='Click button (default: left)')
    parser.add_argument('--timeout-s', type=float, default=None, help='Max seconds to wait for click coordinate (default: 10.0)')
    parser.add_argument('--focus-action-window', action=argparse.BooleanOptionalAction, default=None, help='Try to focus action window before clicking (default: on)')
    parser.add_argument('--focus-after-s', type=float, default=None, help='Seconds to sleep after focusing (default: 0.10)')
    parser.add_argument('--click-at-cursor', action=argparse.BooleanOptionalAction, default=None, help='Move to point then click at cursor (default: off)')
    parser.add_argument('--pre-delay-s', type=float, default=None, help='Delay before click when using --click-at-cursor (default: 0.15)')
    args = parser.parse_args()

    ctx = dict(base_context)
    ctx['ng_pause'] = False
    ctx['ng_debug'] = {'last_tick_reason': None}
    ctx['ng_diag'] = {}

    out_dir = pathlib.Path('debug')
    out_dir.mkdir(parents=True, exist_ok=True)

    idx = args.index if args.index is not None else int(os.getenv('FENRIL_BATTLELIST_CLICK_INDEX', '0'))
    button = (args.button or os.getenv('FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON', 'left')).strip().lower()
    if button not in {'left', 'right'}:
        button = 'left'

    if args.focus_action_window is None:
        focus_action_window = os.getenv('FENRIL_FOCUS_ACTION_WINDOW', '1') not in {'0', 'false', 'False'}
    else:
        focus_action_window = bool(args.focus_action_window)

    if args.focus_after_s is None:
        try:
            focus_after_s = float(os.getenv('FENRIL_FOCUS_AFTER_S', '0.10'))
        except Exception:
            focus_after_s = 0.10
    else:
        focus_after_s = float(args.focus_after_s)

    if args.timeout_s is None:
        timeout_s = float(os.getenv('FENRIL_TEST_CLICK_TIMEOUT_S', '10.0'))
    else:
        timeout_s = float(args.timeout_s)

    if args.click_at_cursor is None:
        click_at_cursor = os.getenv('FENRIL_TEST_CLICK_AT_CURSOR', '0') in {'1', 'true', 'True'}
    else:
        click_at_cursor = bool(args.click_at_cursor)

    if args.pre_delay_s is None:
        pre_delay_s = float(os.getenv('FENRIL_TEST_CLICK_PRE_DELAY_S', '0.15'))
    else:
        pre_delay_s = float(args.pre_delay_s)

    deadline = time.time() + max(0.0, timeout_s)
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
        focused = _focus_action_window(ctx, enabled=focus_action_window, focus_after_s=focus_after_s)
        print(f"[test] FOUND click={click} abs={abs_click} cap_rect={cap_rect} act_rect={act_rect} idx={idx} button={button}")
        print(f"[test] focus_action_window={focused}")
        print(f"[test] dumped screenshot: {dump_path}")
        if click_at_cursor:
            mouse.moveTo(click)
            time.sleep(max(0.0, pre_delay_s))
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
