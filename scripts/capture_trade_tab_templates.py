"""Capture NPC trade tab templates (Buy/Sell) from the *same* capture pipeline the bot uses.

Why
- Newer Tibia NPC trade UI has Buy/Sell tabs.
- Clicking tabs via fixed offsets can fail with DPI/capture scaling.
- Template matching (with locateMultiScale) is more robust, but needs templates captured from YOUR OBS/capture.

What this does
- Grabs a screenshot using the bot middlewares (same as runtime).
- Opens an interactive ROI picker to select the BUY tab, then the SELL tab.
- Saves grayscale templates into:
  - src/repositories/refill/images/tradeTabs/buy.png
  - src/repositories/refill/images/tradeTabs/sell.png

Usage (PowerShell)
- Ensure capture works (same as running the bot).
- Open the NPC trade window in-game.
- Run:
  `./.venv/Scripts/python.exe scripts/capture_trade_tab_templates.py`

Notes
- This script does NOT download images from the internet.
- Press ENTER or SPACE to accept a selection; press ESC to cancel.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
from typing import Optional

import numpy as np


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware  # noqa: E402
from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware  # noqa: E402
from src.repositories.refill import core as refillCore  # noqa: E402
from src.utils.mouse import leftClick  # noqa: E402
from src.utils.image import save as save_gray  # noqa: E402


def _select_roi(window_name: str, img: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    """Interactive ROI selection using OpenCV UI (optional fallback).

    Returns (x, y, w, h) in image coordinates.
    """
    import cv2  # local import: avoid requiring GUI for auto mode

    roi = cv2.selectROI(window_name, img, showCrosshair=True, fromCenter=False)
    try:
        x, y, w, h = (int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3]))
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _crop_box(img: np.ndarray, cx: int, cy: int, w: int, h: int) -> np.ndarray:
    x0 = max(0, int(cx - w // 2))
    y0 = max(0, int(cy - h // 2))
    x1 = min(int(img.shape[1]), x0 + int(w))
    y1 = min(int(img.shape[0]), y0 + int(h))
    return img[y0:y1, x0:x1]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description='Capture NPC trade Buy/Sell tab templates using the bot capture pipeline.'
    )
    parser.add_argument(
        '--mode',
        choices=['auto', 'interactive'],
        default='auto',
        help='auto: click tabs + crop around expected location (recommended). interactive: manual ROI selection via OpenCV UI.',
    )
    parser.add_argument(
        '--box-w',
        type=int,
        default=54,
        help='Crop box width (auto mode).',
    )
    parser.add_argument(
        '--box-h',
        type=int,
        default=18,
        help='Crop box height (auto mode).',
    )
    parser.add_argument(
        '--capture-title',
        type=str,
        default=None,
        help='OBS projector (capture) window title substring/exact title. Overrides ng_runtime.capture_window_title.',
    )
    parser.add_argument(
        '--action-title',
        type=str,
        default=None,
        help='Tibia (action) window title substring/exact title. Overrides ng_runtime.action_window_title.',
    )
    parser.add_argument(
        '--dump-on-fail',
        action='store_true',
        help='If trade window not detected, dump the captured frame to debug/ for inspection.',
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    ctx: dict = {}
    if args.capture_title or args.action_title:
        ctx['ng_runtime'] = {}
        if args.capture_title:
            ctx['ng_runtime']['capture_window_title'] = str(args.capture_title)
        if args.action_title:
            ctx['ng_runtime']['action_window_title'] = str(args.action_title)

    ctx = setTibiaWindowMiddleware(ctx)
    ctx = setScreenshotMiddleware(ctx)

    screenshot = ctx.get('ng_screenshot')
    if screenshot is None:
        raise RuntimeError('Failed to capture screenshot. Check OBS/projector capture settings.')

    # Ensure numpy array.
    img = np.asarray(screenshot)

    out_dir = REPO_ROOT / 'src' / 'repositories' / 'refill' / 'images' / 'tradeTabs'
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == 'interactive':
        import cv2  # local import

        # selectROI behaves better on 3-channel; show grayscale as BGR.
        if img.ndim == 2:
            preview = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            preview = img

        print('Select ROI for BUY tab (press ENTER/SPACE to confirm, ESC to cancel)')
        buy_roi = _select_roi('Select BUY tab', preview)
        if buy_roi is None:
            print('Canceled / invalid ROI for BUY tab.')
            cv2.destroyAllWindows()
            return 2

        print('Select ROI for SELL tab (press ENTER/SPACE to confirm, ESC to cancel)')
        sell_roi = _select_roi('Select SELL tab', preview)
        if sell_roi is None:
            print('Canceled / invalid ROI for SELL tab.')
            cv2.destroyAllWindows()
            return 2

        cv2.destroyAllWindows()

        bx, by, bw, bh = buy_roi
        sx, sy, sw, sh = sell_roi
        buy_crop = img[by : by + bh, bx : bx + bw]
        sell_crop = img[sy : sy + sh, sx : sx + sw]

        if buy_crop.ndim == 3:
            buy_crop = cv2.cvtColor(buy_crop, cv2.COLOR_RGB2GRAY)
        if sell_crop.ndim == 3:
            sell_crop = cv2.cvtColor(sell_crop, cv2.COLOR_RGB2GRAY)

        buy_path = out_dir / 'buy.png'
        sell_path = out_dir / 'sell.png'
        save_gray(np.asarray(buy_crop, dtype=np.uint8), str(buy_path))
        save_gray(np.asarray(sell_crop, dtype=np.uint8), str(sell_path))
        print(f'[ok] wrote {buy_path}')
        print(f'[ok] wrote {sell_path}')
        print('Tip: if matching is unstable, capture again with a tighter ROI including the tab label.')
        return 0

    # AUTO mode: anchor to trade window, click tabs, and crop around the expected tab position.
    top = refillCore.getTradeTopPosition(img)
    if top is None:
        if args.dump_on_fail:
            try:
                import os
                import cv2

                out_dir_dbg = REPO_ROOT / 'debug'
                out_dir_dbg.mkdir(parents=True, exist_ok=True)
                fp = out_dir_dbg / 'trade_tab_capture_no_trade_window.png'
                # cv2 expects BGR; img is Gray or RGB.
                arr = img
                if arr.ndim == 3:
                    arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                cv2.imwrite(str(fp), arr)
                print(f'[dump] wrote {fp}')
            except Exception:
                pass

        # Help the user understand what window is being captured.
        try:
            dbg = ctx.get('ng_debug') if isinstance(ctx.get('ng_debug'), dict) else None
            cap_title = None
            if isinstance(dbg, dict):
                cap_title = dbg.get('capture_window_title')
            else:
                cap_title = None
            print(f"[info] capture_window_title={cap_title!r}")
        except Exception:
            pass

        raise RuntimeError(
            'Trade window not detected in the CAPTURE image. Make sure OBS projector is the capture window and the NPC trade window is visible in that capture.'
        )

    (tx, ty, _, _) = top
    buy_click = (int(tx + 155), int(ty + 30))
    sell_click = (int(tx + 155), int(ty + 52))

    def _refresh() -> np.ndarray:
        nonlocal ctx
        ctx = setScreenshotMiddleware(ctx)
        shot = ctx.get('ng_screenshot')
        if shot is None:
            raise RuntimeError('Failed to refresh screenshot during capture.')
        return np.asarray(shot)

    # Capture BUY template
    leftClick(buy_click)
    time.sleep(0.25)
    img2 = _refresh()
    buy_crop = _crop_box(img2, buy_click[0], buy_click[1], int(args.box_w), int(args.box_h))

    # Capture SELL template
    leftClick(sell_click)
    time.sleep(0.25)
    img3 = _refresh()
    sell_crop = _crop_box(img3, sell_click[0], sell_click[1], int(args.box_w), int(args.box_h))

    # Ensure grayscale
    if buy_crop.ndim == 3:
        import cv2  # local import

        buy_crop = cv2.cvtColor(buy_crop, cv2.COLOR_RGB2GRAY)
    if sell_crop.ndim == 3:
        import cv2  # local import

        sell_crop = cv2.cvtColor(sell_crop, cv2.COLOR_RGB2GRAY)

    buy_path = out_dir / 'buy.png'
    sell_path = out_dir / 'sell.png'
    save_gray(np.asarray(buy_crop, dtype=np.uint8), str(buy_path))
    save_gray(np.asarray(sell_crop, dtype=np.uint8), str(sell_path))

    print(f'[ok] wrote {buy_path}')
    print(f'[ok] wrote {sell_path}')
    print('Tip: if matching is unstable, rerun with smaller box (--box-w/--box-h) to capture only the tab label.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
