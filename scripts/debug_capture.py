import pathlib
import sys
import os
import time
import runpy

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np

from src.utils.core import (
    getMonitorRectForPoint,
    getScreenshot,
    getScreenshotDebugInfo,
    setScreenshotOutputIdx,
)
from src.repositories.radar.locators import getRadarToolsPosition
from src.repositories.gameWindow.core import getLeftArrowPosition, getRightArrowPosition


def main() -> None:
    # If dual-window env vars are set, run the dual debug tool instead.
    # This avoids confusion where FENRIL_WINDOW_TITLE (legacy) makes it look
    # like we're capturing the Tibia monitor even though the bot is configured
    # for an OBS projector capture.
    if os.getenv('FENRIL_CAPTURE_WINDOW_TITLE') or os.getenv('FENRIL_ACTION_WINDOW_TITLE'):
        dual = ROOT / 'scripts' / 'debug_capture_dual.py'
        print('[fenril][dual] Detected dual-window env vars; running scripts/debug_capture_dual.py')
        runpy.run_path(str(dual), run_name='__main__')
        return

    region: Optional[tuple[int, int, int, int]] = None
    region_abs: Optional[tuple[int, int, int, int]] = None
    window_title = os.getenv('FENRIL_WINDOW_TITLE')
    if window_title:
        try:
            import pygetwindow as gw

            windows = gw.getWindowsWithTitle(window_title)
            if windows:
                w = windows[0]
                # Optionally bring to foreground so desktop capture sees it.
                activate = os.getenv('FENRIL_ACTIVATE_WINDOW', '1') != '0'
                if activate:
                    try:
                        if getattr(w, 'isMinimized', False):
                            w.restore()
                        w.activate()
                        time.sleep(0.15)
                    except Exception as e:
                        print(f"Failed to activate window: {type(e).__name__}: {e}")
                left = int(w.left)
                top = int(w.top)
                right = left + int(w.width)
                bottom = top + int(w.height)
                region_abs = (left, top, right, bottom)
                # Keep a clamped absolute region for display only.
                region = (max(0, left), max(0, top), right, bottom)
                print(f"Using window region for '{window_title}': {region}")
            else:
                print(f"No window found with title containing: {window_title!r}")
        except Exception as e:
            print(f"Failed to resolve window region: {type(e).__name__}: {e}")

    out_dir = pathlib.Path('debug')
    out_dir.mkdir(parents=True, exist_ok=True)

    from typing import Optional

    def _report(tag: str, frame: Optional[np.ndarray]) -> None:
        print(f"\n=== {tag} ===")
        if frame is None:
            print('img=None')
            return
        mean_val = float(np.mean(frame))
        std_val = float(np.std(frame))
        print(f"shape={frame.shape} dtype={frame.dtype} mean={mean_val:.2f} std={std_val:.2f}")
        tools_pos = getRadarToolsPosition(frame)
        left_arrow = getLeftArrowPosition(frame)
        right_arrow = getRightArrowPosition(frame)
        print(f"radarToolsPosition={tools_pos}")
        print(f"leftArrowPosition={left_arrow}")
        print(f"rightArrowPosition={right_arrow}")

    # Try common monitor indices so multi-monitor setups are easy to diagnose.
    for idx in (0, 1):
        try:
            setScreenshotOutputIdx(idx)
        except Exception as e:
            print(f"Failed to set output_idx={idx}: {type(e).__name__}: {e}")
            continue

        full = getScreenshot()
        info_full = getScreenshotDebugInfo()
        print('\n=== Screenshot Debug (global) ===')
        print(f"output_idx={info_full.get('output_idx')} stale(grab None)={info_full.get('last_grab_was_none')}")
        print(f"none_frames={info_full.get('consecutive_none_frames')} black_frames={info_full.get('consecutive_black_frames')}")

        if full is not None:
            full_path = out_dir / f'debug_fullscreen_idx{idx}_gray.png'
            cv2.imwrite(str(full_path), full)
            print(f"Saved: {full_path}")
        _report(f'Fullscreen (idx={idx})', full)

        if region_abs is not None:
            # Translate the absolute window coords into monitor-relative coords.
            cx = int((region_abs[0] + region_abs[2]) // 2)
            cy = int((region_abs[1] + region_abs[3]) // 2)
            mon = getMonitorRectForPoint(cx, cy)
            if mon is not None:
                mon_left, mon_top, _, _ = mon
                region_rel = (
                    max(0, region_abs[0] - mon_left),
                    max(0, region_abs[1] - mon_top),
                    max(0, region_abs[2] - mon_left),
                    max(0, region_abs[3] - mon_top),
                )
            else:
                # If we couldn't resolve the monitor, fall back to clamped absolute coords.
                # This will be correct on single-monitor or primary-monitor-at-(0,0) setups.
                region_rel = (
                    max(0, region_abs[0]),
                    max(0, region_abs[1]),
                    max(0, region_abs[2]),
                    max(0, region_abs[3]),
                )

            region_frame = getScreenshot(region=region_rel)
            if region_frame is not None:
                region_path = out_dir / f'debug_window_region_idx{idx}_gray.png'
                cv2.imwrite(str(region_path), region_frame)
                print(f"Saved: {region_path}")
            _report(f'Window Region (idx={idx})', region_frame)


if __name__ == '__main__':
    main()
