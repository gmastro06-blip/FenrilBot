"""Capture NPC trade window templates (bar + OK) from OBS/projector capture.

Why
- If `npcTradeBar.png` / `npcTradeOk.png` don't match your client UI (theme/DPI/scaling),
  the bot can't detect the NPC trade window.
- This script captures a frame from the same capture pipeline the bot uses (OBS projector),
  then lets you select ROIs for the trade bar and OK button.

What this does
- Grabs a screenshot using the bot middlewares.
- Opens interactive ROI pickers to select:
  - Trade bar area (top of trade window)
  - OK button area (bottom of trade window)
- Saves grayscale templates as *variants* (doesn't overwrite repo defaults):
  - src/repositories/refill/images/npcTradeBar_<suffix>.png
  - src/repositories/refill/images/npcTradeOk_<suffix>.png

Usage (PowerShell)
- Open NPC trade window in-game, make sure it's visible in OBS projector.
- Run:
  `./.venv/Scripts/python.exe scripts/capture_trade_window_templates.py --capture-title "<OBS projector title>"`

Notes
- Press ENTER or SPACE to accept a selection; press ESC to cancel.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Optional

import numpy as np


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware  # noqa: E402
from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware  # noqa: E402
from src.utils.image import save as save_gray  # noqa: E402


def _select_roi(window_name: str, img: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    import cv2

    roi = cv2.selectROI(window_name, img, showCrosshair=True, fromCenter=False)
    try:
        x, y, w, h = (int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3]))
    except Exception:
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description='Capture NPC trade window templates (bar/ok) using the bot capture pipeline.'
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
        '--suffix',
        type=str,
        default='user',
        help='Suffix used for filenames, e.g. npcTradeBar_<suffix>.png',
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

    img = np.asarray(screenshot)

    # selectROI behaves best with 3-channel images.
    import cv2

    if img.ndim == 2:
        preview = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        preview = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    print('Select ROI for NPC trade BAR (top bar)')
    bar_roi = _select_roi('Select NPC trade BAR', preview)
    if bar_roi is None:
        cv2.destroyAllWindows()
        print('Canceled / invalid ROI for BAR.')
        return 2

    print('Select ROI for NPC trade OK button')
    ok_roi = _select_roi('Select NPC trade OK', preview)
    if ok_roi is None:
        cv2.destroyAllWindows()
        print('Canceled / invalid ROI for OK.')
        return 2

    cv2.destroyAllWindows()

    bx, by, bw, bh = bar_roi
    ox, oy, ow, oh = ok_roi

    bar_crop = preview[by : by + bh, bx : bx + bw]
    ok_crop = preview[oy : oy + oh, ox : ox + ow]

    bar_gray = cv2.cvtColor(bar_crop, cv2.COLOR_BGR2GRAY)
    ok_gray = cv2.cvtColor(ok_crop, cv2.COLOR_BGR2GRAY)

    out_dir = REPO_ROOT / 'src' / 'repositories' / 'refill' / 'images'
    out_dir.mkdir(parents=True, exist_ok=True)

    bar_path = out_dir / f'npcTradeBar_{args.suffix}.png'
    ok_path = out_dir / f'npcTradeOk_{args.suffix}.png'

    save_gray(np.asarray(bar_gray, dtype=np.uint8), str(bar_path))
    save_gray(np.asarray(ok_gray, dtype=np.uint8), str(ok_path))

    print(f'[ok] wrote {bar_path}')
    print(f'[ok] wrote {ok_path}')
    print('Next: rerun scripts/capture_trade_tab_templates.py (auto mode) to capture buy/sell tabs.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
