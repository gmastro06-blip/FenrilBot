from src.utils.core import (
    getMonitorRectForPoint,
    getOutputIdxForPoint,
    getScreenshot,
    getScreenshotDebugInfo,
    setScreenshotOutputIdx,
)
from src.gameplay.typings import Context
from src.utils.mouse import set_window_transform

import cv2
import numpy as np
import os
import pathlib
import time
from typing import Optional, Tuple


def _get_client_rect_screen(window: object) -> Optional[Tuple[int, int, int, int]]:
    """Return (left, top, width, height) of the window client area in screen coords."""
    try:
        import win32gui

        hwnd = getattr(window, '_hWnd', None)
        if hwnd is None:
            return None
        left, top = win32gui.ClientToScreen(hwnd, (0, 0))
        _, _, w, h = win32gui.GetClientRect(hwnd)
        if w <= 0 or h <= 0:
            return None
        return (int(left), int(top), int(w), int(h))
    except Exception:
        return None


# TODO: add unit tests
def setScreenshotMiddleware(context: Context) -> Context:
    region = None
    absolute_region = None
    capture_window = context.get('capture_window') or context.get('window')
    action_window = context.get('action_window') or context.get('window')

    capture_rect = None
    action_rect = None

    if action_window is not None:
        try:
            client = _get_client_rect_screen(action_window)
            if client is not None:
                action_left, action_top, action_w, action_h = client
            else:
                action_left = int(action_window.left)
                action_top = int(action_window.top)
                action_w = int(action_window.width)
                action_h = int(action_window.height)
            action_right = action_left + action_w
            action_bottom = action_top + action_h
            ax = action_left + max(0, action_w // 2)
            ay = action_top + max(0, action_h // 2)
            action_mon = getMonitorRectForPoint(ax, ay)
            if action_mon is not None:
                ml, mt, mr, mb = action_mon
                il = max(action_left, ml)
                it = max(action_top, mt)
                ir = min(action_right, mr)
                ib = min(action_bottom, mb)
                if ir > il and ib > it:
                    action_rect = (il, it, ir - il, ib - it)
                else:
                    action_rect = None
            else:
                action_rect = (max(0, action_left), max(0, action_top), action_w, action_h)
        except Exception:
            action_rect = None

    debug = context.get('ng_debug') if isinstance(context.get('ng_debug'), dict) else None

    if capture_window is not None:
        try:
            client = _get_client_rect_screen(capture_window)
            if client is not None:
                left, top, w, h = client
            else:
                left = int(capture_window.left)
                top = int(capture_window.top)
                w = int(capture_window.width)
                h = int(capture_window.height)
            right = left + w
            bottom = top + h

            # Figure out which monitor the window is on and switch dxcam output accordingly.
            cx = left + max(0, w // 2)
            cy = top + max(0, h // 2)
            output_idx = getOutputIdxForPoint(cx, cy)
            auto_output = os.getenv('FENRIL_AUTO_OUTPUT_IDX', '1') != '0'
            if auto_output and output_idx is not None:
                current_idx = getScreenshotDebugInfo().get('output_idx')
                if current_idx != output_idx:
                    setScreenshotOutputIdx(int(output_idx))

            mon = getMonitorRectForPoint(cx, cy)
            if mon is not None:
                mon_left, mon_top, mon_right, mon_bottom = mon
                # Use the visible intersection with the monitor bounds.
                il = max(left, mon_left)
                it = max(top, mon_top)
                ir = min(right, mon_right)
                ib = min(bottom, mon_bottom)
                if ir > il and ib > it:
                    capture_rect = (il, it, ir - il, ib - it)
                    # dxcam region is relative to the selected output.
                    region = (
                        max(0, il - mon_left),
                        max(0, it - mon_top),
                        max(0, ir - mon_left),
                        max(0, ib - mon_top),
                    )
                    absolute_region = (il, it, ir, ib)
                else:
                    capture_rect = None
                    region = None
                    absolute_region = None
                if debug is not None:
                    debug['capture_window_monitor_rect'] = mon
                    debug['capture_window_output_idx'] = output_idx
            else:
                # Fallback: at least clamp negatives.
                cl = max(0, left)
                ct = max(0, top)
                cr = max(cl + 1, right)
                cb = max(ct + 1, bottom)
                capture_rect = (cl, ct, cr - cl, cb - ct)
                region = (cl, ct, cr, cb)
                absolute_region = (cl, ct, cr, cb)
        except Exception:
            region = None
            absolute_region = None

    context['ng_capture_rect'] = capture_rect
    context['ng_action_rect'] = action_rect
    # Store capture regions so tasks can refresh the screenshot consistently.
    context['ng_capture_region'] = region
    context['ng_capture_absolute_region'] = absolute_region
    try:
        context['ng_capture_output_idx'] = getScreenshotDebugInfo().get('output_idx')
    except Exception:
        context['ng_capture_output_idx'] = None
    set_window_transform(capture_rect, action_rect)

    context['ng_screenshot'] = getScreenshot(region=region, absolute_region=absolute_region)

    # Diagnostics: detect black/empty capture and dump a frame periodically.
    diag = context.get('ng_diag') if isinstance(context.get('ng_diag'), dict) else None
    if diag is None:
        diag = {}
        context['ng_diag'] = diag

    screenshot = context.get('ng_screenshot')
    if screenshot is not None:
        try:
            mean_val = float(np.mean(screenshot))
            std_val = float(np.std(screenshot))
            diag['capture_mean'] = mean_val
            diag['capture_std'] = std_val
            std_thr = float(os.getenv('FENRIL_BLACK_STD_THRESHOLD', '2.0'))
            mean_thr = float(os.getenv('FENRIL_BLACK_MEAN_THRESHOLD', '10.0'))
            mean_force_thr = float(os.getenv('FENRIL_BLACK_MEAN_FORCE_THRESHOLD', '3.0'))
            dark_px_thr = int(os.getenv('FENRIL_BLACK_DARK_PIXEL_THRESHOLD', '8'))
            dark_frac_thr = float(os.getenv('FENRIL_BLACK_DARK_FRACTION_THRESHOLD', '0.98'))
            dark_fraction = float(np.mean(screenshot <= dark_px_thr))
            diag['capture_dark_fraction'] = dark_fraction
            is_black = (mean_val < mean_thr) and (
                mean_val <= mean_force_thr or std_val < std_thr or dark_fraction >= dark_frac_thr
            )
        except Exception:
            is_black = False

        if is_black:
            diag['consecutive_black_capture'] = int(diag.get('consecutive_black_capture', 0)) + 1
        else:
            diag['consecutive_black_capture'] = 0

        black_dump_threshold = int(os.getenv('FENRIL_DIAG_BLACK_DUMP_THRESHOLD', '12'))
        # Dumping black frames is useful during setup, but can flood `debug/` in long runs.
        # Default is OFF; enable with FENRIL_DUMP_BLACK_CAPTURE=1.
        if (
            os.getenv('FENRIL_DUMP_BLACK_CAPTURE', '0') in {'1', 'true', 'True'}
            and int(diag.get('consecutive_black_capture', 0)) >= black_dump_threshold
        ):
            last_dump = float(diag.get('last_black_dump_time', 0.0))
            now = time.time()
            # Avoid spamming dumps.
            min_interval = float(os.getenv('FENRIL_DUMP_BLACK_CAPTURE_MIN_INTERVAL_S', '60.0'))
            if now - last_dump >= min_interval:
                diag['last_black_dump_time'] = now
                out_dir = pathlib.Path('debug')
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f'dual_capture_black_{int(now)}.png'
                try:
                    cv2.imwrite(str(path), screenshot)
                    backend = None
                    try:
                        backend = getScreenshotDebugInfo().get('last_stats', {}).get('backend')
                    except Exception:
                        backend = None
                    print(
                        f"[fenril][dual] Black capture detected (mean={diag.get('capture_mean'):.2f} std={diag.get('capture_std'):.2f} backend={backend}) - dumped {path}"
                    )
                except Exception:
                    pass

    if debug is not None:
        debug['screenshot'] = getScreenshotDebugInfo()
        if context['ng_screenshot'] is None:
            debug['last_tick_reason'] = 'no screenshot'
    return context
