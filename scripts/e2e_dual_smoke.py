"""End-to-end dual-window smoke test (OBS projector + Tibia).

Goal: collect a concrete, reproducible report for the most common full-flow blockers:
- window resolution (capture/action)
- capture output index / region
- screenshot black/None issues
- radar tools locator sanity
- battlelist click coordinate extraction sanity
- capture->action transform sanity

This script is designed to run WITHOUT exporting FENRIL_* env vars.

Example:
  ./.venv/Scripts/python.exe -u scripts/e2e_dual_smoke.py \
    --capture-title "Proyector en ventana (Fuente) - Tibia_Fuente" \
    --action-title "Tibia - YourCharacter" \
    --frames 5 --interval 0.2 --battlelist-index 0
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
from datetime import datetime
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
from src.repositories.radar.locators import getRadarToolsPosition
import src.utils.mouse as mouse


def _ts() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S_%f')


def _dump(out_dir: pathlib.Path, name: str, img: np.ndarray) -> pathlib.Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}_{_ts()}.png"
    cv2.imwrite(str(path), np.ascontiguousarray(img))
    return path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Fenril E2E dual-window smoke test')
    parser.add_argument('--capture-title', required=True, type=str, help='OBS projector window title (exact or substring)')
    parser.add_argument('--action-title', required=True, type=str, help='Tibia client window title (exact or substring)')
    parser.add_argument('--frames', type=int, default=5, help='Number of frames to sample (default: 5)')
    parser.add_argument('--interval', type=float, default=0.2, help='Seconds to sleep between frames (default: 0.2)')
    parser.add_argument('--battlelist-index', type=int, default=0, help='Battlelist index to extract click coordinate for (default: 0)')
    parser.add_argument('--save-all', action='store_true', help='Dump every sampled frame to debug/')
    args = parser.parse_args(argv)

    ctx = dict(base_context)
    # Make sure we don't mutate global dicts across runs.
    ctx['ng_debug'] = {'last_tick_reason': None, 'last_exception': None}
    ctx['ng_diag'] = {}

    ng_runtime = dict(cast(dict, ctx.get('ng_runtime', {})))
    ng_runtime['capture_window_title'] = str(args.capture_title)
    ng_runtime['action_window_title'] = str(args.action_title)
    # Useful in dual setups.
    ng_runtime.setdefault('auto_output_idx', True)
    # Better operator feedback.
    ng_runtime.setdefault('warn_on_window_miss', True)
    ctx['ng_runtime'] = ng_runtime

    out_dir = pathlib.Path('debug')

    print('=== Fenril E2E Dual Smoke ===')
    print(f"capture_title={args.capture_title!r}")
    print(f"action_title={args.action_title!r}")

    last: Optional[np.ndarray] = None
    first_ctx = None

    for i in range(max(1, int(args.frames))):
        if i > 0:
            time.sleep(max(0.0, float(args.interval)))

        ctx = setTibiaWindowMiddleware(ctx)
        ctx = setScreenshotMiddleware(ctx)

        if first_ctx is None:
            first_ctx = dict(ctx)

        shot = ctx.get('ng_screenshot')
        if shot is None:
            print(f"frame[{i}]: screenshot=None")
            continue

        shot_np = cast(np.ndarray, shot)
        last = shot_np

        mean_val = float(np.mean(shot_np))
        std_val = float(np.std(shot_np))

        tools_pos = None
        try:
            tools_pos = getRadarToolsPosition(shot_np)
        except Exception as e:
            print(f"frame[{i}]: radarTools error {type(e).__name__}: {e}")

        click = None
        try:
            click = battlelist_extractors.getCreatureClickCoordinate(shot_np, index=int(args.battlelist_index))
        except Exception as e:
            print(f"frame[{i}]: battlelist click error {type(e).__name__}: {e}")

        cap_rect, act_rect = mouse.get_window_transform()
        abs_click = mouse.transform_capture_to_action(click) if click is not None else None

        print(
            f"frame[{i}] shape={shot_np.shape} mean={mean_val:.2f} std={std_val:.2f} "
            f"radarTools={tools_pos} battlelistClick={click} absClick={abs_click}"
        )

        if i == 0 or args.save_all or tools_pos is None or click is None:
            p = _dump(out_dir, f"e2e_dual_smoke_{i}", shot_np)
            print(f"  dumped: {p}")

        # Print transform info once.
        if i == 0:
            print(f"capture_rect={cap_rect}")
            print(f"action_rect={act_rect}")
            try:
                ng_debug = ctx.get('ng_debug')
                if isinstance(ng_debug, dict):
                    info = ng_debug.get('screenshot')
                    if info is not None:
                        print(f"screenshot_debug={info}")
            except Exception:
                pass

    if last is None:
        print('FAIL: never got a screenshot. Likely window resolution/capture is broken.')
        if first_ctx is not None:
            try:
                print(f"ng_window={first_ctx.get('ng_window')}")
                print(f"ng_capture_rect={first_ctx.get('ng_capture_rect')} ng_action_rect={first_ctx.get('ng_action_rect')}")
                print(f"ng_capture_output_idx={first_ctx.get('ng_capture_output_idx')}")
            except Exception:
                pass
        return 2

    print('OK: captured at least one frame. Review dumped images and the per-frame radar/battlelist outputs above.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
