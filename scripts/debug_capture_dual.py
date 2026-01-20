import pathlib
import sys
import os
import time
import argparse
from typing import Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
import pygetwindow as gw
from typing import Callable

import importlib

core = importlib.import_module('src.utils.core')

getMonitorRectForPoint = getattr(core, 'getMonitorRectForPoint', None)
getOutputIdxForPoint = getattr(core, 'getOutputIdxForPoint', None)
getScreenshot = getattr(core, 'getScreenshot', None)
getScreenshotDebugInfo = getattr(core, 'getScreenshotDebugInfo', None)
setScreenshotOutputIdx = getattr(core, 'setScreenshotOutputIdx', None)

getRadarToolsPosition: Optional[Callable[[np.ndarray], Optional[Tuple[int, int, int, int]]]] = None
try:
    from src.repositories.radar.locators import getRadarToolsPosition as _getRadarToolsPosition

    getRadarToolsPosition = _getRadarToolsPosition
except Exception:  # pragma: no cover
    pass

getLeftArrowPosition: Optional[Callable[[np.ndarray], Optional[Tuple[int, int, int, int]]]] = None
getRightArrowPosition: Optional[Callable[[np.ndarray], Optional[Tuple[int, int, int, int]]]] = None
try:
    from src.repositories.gameWindow.core import (
        getLeftArrowPosition as _getLeftArrowPosition,
        getRightArrowPosition as _getRightArrowPosition,
    )

    getLeftArrowPosition = _getLeftArrowPosition
    getRightArrowPosition = _getRightArrowPosition
except Exception:  # pragma: no cover
    pass


Rect = Tuple[int, int, int, int]  # (left, top, width, height)


def _client_rect(w: gw.Win32Window) -> Rect:
    """Client area rect in screen coordinates (falls back to full window rect)."""
    try:
        import win32gui

        hwnd = getattr(w, '_hWnd', None)
        if hwnd is not None:
            left, top = win32gui.ClientToScreen(hwnd, (0, 0))
            _, _, cw, ch = win32gui.GetClientRect(hwnd)
            if cw > 0 and ch > 0:
                return (int(left), int(top), int(cw), int(ch))
    except Exception:
        pass
    return (int(w.left), int(w.top), int(w.width), int(w.height))


def _visible_rect_on_monitor(rect: Rect) -> Tuple[Optional[Rect], Optional[Tuple[int, int, int, int]]]:
    left, top, w, h = rect
    right = left + w
    bottom = top + h
    cx = left + max(0, w // 2)
    cy = top + max(0, h // 2)
    if getMonitorRectForPoint is None:
        return rect, None
    mon = getMonitorRectForPoint(cx, cy)
    if mon is None:
        cl = max(0, left)
        ct = max(0, top)
        cr = max(cl + 1, right)
        cb = max(ct + 1, bottom)
        return (cl, ct, cr - cl, cb - ct), None
    ml, mt, mr, mb = mon
    il = max(left, ml)
    it = max(top, mt)
    ir = min(right, mr)
    ib = min(bottom, mb)
    if ir <= il or ib <= it:
        return None, mon
    return (il, it, ir - il, ib - it), mon


def _resolve_exact_title(title: str) -> Optional[gw.Win32Window]:
    wins = gw.getWindowsWithTitle(title)
    for w in wins:
        if getattr(w, "title", None) == title:
            return w
    return None


def _resolve_tibia_fallback() -> Optional[gw.Win32Window]:
    # Keep it simple here: substring lookup.
    wins = gw.getWindowsWithTitle("Tibia")
    return wins[0] if wins else None


def _map_capture_to_action(local_xy: Tuple[int, int], capture_rect: Rect, action_rect: Rect) -> Tuple[int, int]:
    cap_left, cap_top, cap_w, cap_h = capture_rect
    act_left, act_top, act_w, act_h = action_rect
    x, y = local_xy
    ax = act_left + (x * act_w / max(1, cap_w))
    ay = act_top + (y * act_h / max(1, cap_h))
    return (int(round(ax)), int(round(ay)))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description='Fenril dual-window capture debug')
    parser.add_argument('--frames', type=int, default=1, help='Number of frames to capture (default: 1)')
    parser.add_argument('--interval', type=float, default=0.2, help='Seconds to sleep between frames (default: 0.2)')
    parser.add_argument('--save', action='store_true', help='Save each captured frame to debug/ (default: only saves first)')
    args = parser.parse_args(argv)

    capture_title = os.getenv("FENRIL_CAPTURE_WINDOW_TITLE")
    action_title = os.getenv("FENRIL_ACTION_WINDOW_TITLE")

    # Helpful default: if capture title isn't provided, try to auto-detect an OBS projector.
    if not capture_title:
        projector_patterns = [
            "Proyector en ventana",  # Spanish OBS
            "Projector",            # English OBS
            "OBS",                  # generic
        ]
        wins = gw.getAllWindows()
        candidates = [w for w in wins if getattr(w, 'title', '')]
        projector_candidates = []
        for w in candidates:
            title = getattr(w, 'title', '')
            if any(p.lower() in title.lower() for p in projector_patterns):
                projector_candidates.append(w)
        # Prefer the known default title if present.
        for w in projector_candidates:
            if getattr(w, 'title', None) == "Proyector en ventana (Fuente) - Tibia_Fuente":
                capture_title = "Proyector en ventana (Fuente) - Tibia_Fuente"
                break
        # Otherwise, if there is a single candidate, pick it.
        if not capture_title and len(projector_candidates) == 1:
            capture_title = getattr(projector_candidates[0], 'title', None)

        if not capture_title:
            # Print a short list of likely candidates for copy/paste.
            print("WARN: FENRIL_CAPTURE_WINDOW_TITLE not set and no unique OBS projector found.")
            print("Candidates containing projector/obs:")
            for w in projector_candidates[:10]:
                print(f"  - {getattr(w, 'title', '')}")

    action_window = None
    if action_title:
        action_window = _resolve_exact_title(action_title)
        if action_window is None:
            print(f"[warn] Could not find action window with exact title: {action_title!r}")
    if action_window is None:
        action_window = _resolve_tibia_fallback()

    capture_window = None
    if capture_title:
        capture_window = _resolve_exact_title(capture_title)
        if capture_window is None:
            print(f"[warn] Could not find capture window with exact title: {capture_title!r}")
            try:
                titles = [t for t in gw.getAllTitles() if t and t.strip()]
                needles = []
                if capture_title:
                    needles.append(capture_title)
                needles.extend(["Projector", "OBS", "Fuente", "Tibia_Fuente", "Windowed Projector"])
                candidates = [t for t in titles if any(n.lower() in t.lower() for n in needles)]
                if candidates:
                    print("[info] Candidate window titles (partial match):")
                    for t in candidates[:20]:
                        print(f"  - {t}")
            except Exception:
                pass
    if capture_window is None:
        capture_window = action_window

    print("=== Dual Capture Debug ===")
    print(f"FENRIL_ACTION_WINDOW_TITLE={action_title!r}")
    print(f"FENRIL_CAPTURE_WINDOW_TITLE={capture_title!r}")

    if action_window is None:
        print("action_window: None (could not resolve)")
        return

    if capture_window is None:
        print("capture_window: None (could not resolve)")
        return

    action_rect = _client_rect(action_window)
    capture_rect = _client_rect(capture_window)

    action_rect_vis, action_mon = _visible_rect_on_monitor(action_rect)
    capture_rect_vis, capture_mon = _visible_rect_on_monitor(capture_rect)

    if action_rect_vis is None:
        print(f"action_rect not visible on monitor (monitor={action_mon})")
        return
    if capture_rect_vis is None:
        print(f"capture_rect not visible on monitor (monitor={capture_mon})")
        return

    action_rect = action_rect_vis
    capture_rect = capture_rect_vis

    print(f"action_window.title={getattr(action_window, 'title', None)!r}")
    print(f"capture_window.title={getattr(capture_window, 'title', None)!r}")
    print(f"action_rect(left,top,w,h)={action_rect}")
    print(f"capture_rect(left,top,w,h)={capture_rect}")

    # Build dxcam region for capture_window visible rect.
    cap_left, cap_top, cap_w, cap_h = capture_rect
    cap_right = cap_left + cap_w
    cap_bottom = cap_top + cap_h

    cx = cap_left + max(0, cap_w // 2)
    cy = cap_top + max(0, cap_h // 2)

    auto_output = os.getenv('FENRIL_AUTO_OUTPUT_IDX', '1') != '0'
    output_idx = getOutputIdxForPoint(cx, cy) if getOutputIdxForPoint is not None else None
    mon = getMonitorRectForPoint(cx, cy) if getMonitorRectForPoint is not None else None

    if mon is None:
        region = (max(0, cap_left), max(0, cap_top), cap_right, cap_bottom)
        absolute_region = region
        output_candidates = [output_idx, 0, 1]
        print(f"monitor_rect=None, using clamped region={region}")
    else:
        mon_left, mon_top, mon_right, mon_bottom = mon
        region = (
            max(0, cap_left - mon_left),
            max(0, cap_top - mon_top),
            max(0, cap_right - mon_left),
            max(0, cap_bottom - mon_top),
        )
        absolute_region = (cap_left, cap_top, cap_right, cap_bottom)
        print(f"monitor_rect={mon} region_rel_to_output={region} output_idx={output_idx}")
        output_candidates = [output_idx, 0, 1]

    # Try a few outputs to make diagnosing multi-monitor setups easier.
    frame = None
    tried = []
    for idx in output_candidates:
        if idx is None or idx in tried:
            continue
        tried.append(idx)
        if auto_output:
            try:
                if setScreenshotOutputIdx is not None:
                    setScreenshotOutputIdx(int(idx))
            except Exception as e:
                print(f"Failed to set output_idx={idx}: {type(e).__name__}: {e}")
                continue
        frame = getScreenshot(region=region, absolute_region=absolute_region) if getScreenshot is not None else None
        info = getScreenshotDebugInfo() if getScreenshotDebugInfo is not None else None
        print("=== Screenshot Debug Info ===")
        print(info)
        if frame is not None:
            break

    out_dir = pathlib.Path('debug')
    out_dir.mkdir(parents=True, exist_ok=True)

    if frame is None:
        print("frame=None")
        return

    std_thr = float(os.getenv('FENRIL_BLACK_STD_THRESHOLD', '2.0'))
    mean_thr = float(os.getenv('FENRIL_BLACK_MEAN_THRESHOLD', '10.0'))

    black_count = 0
    tools_missing = 0
    left_missing = 0
    right_missing = 0

    for i in range(max(1, int(args.frames))):
        if i > 0:
            time.sleep(max(0.0, float(args.interval)))
            frame = getScreenshot(region=region, absolute_region=absolute_region) if getScreenshot is not None else None
            if frame is None:
                print(f"frame[{i}]=None")
                continue

        mean_val = float(np.mean(frame))
        std_val = float(np.std(frame))
        is_black = std_val < std_thr and mean_val < mean_thr
        if is_black:
            black_count += 1

        tools_pos = None
        if getRadarToolsPosition is not None:
            tools_pos = getRadarToolsPosition(frame)
            if tools_pos is None:
                tools_missing += 1

        left_arrow = None
        right_arrow = None
        if getLeftArrowPosition is not None and getRightArrowPosition is not None:
            left_arrow = getLeftArrowPosition(frame)
            right_arrow = getRightArrowPosition(frame)
            if left_arrow is None:
                left_missing += 1
            if right_arrow is None:
                right_missing += 1

        if i == 0 or args.save or is_black or tools_pos is None:
            ts = int(time.time())
            path = out_dir / f"debug_dual_capture_{ts}_gray_{i}.png"
            cv2.imwrite(str(path), frame)
            print(f"Saved: {path}")

        print(
            f"frame[{i}] shape={frame.shape} mean={mean_val:.2f} std={std_val:.2f} is_black={is_black} "
            f"radarTools={tools_pos} leftArrow={left_arrow} rightArrow={right_arrow}"
        )

    if args.frames > 1:
        print("=== Summary ===")
        print(f"frames={args.frames} black={black_count} radarToolsMissing={tools_missing} leftMissing={left_missing} rightMissing={right_missing}")

    print("=== Transform Check (capture-local -> action-absolute) ===")
    points = [
        (0, 0),
        (10, 10),
        (capture_rect[2] // 2, capture_rect[3] // 2),
        (max(0, capture_rect[2] - 50), 50),
    ]
    for p in points:
        mapped = _map_capture_to_action(p, capture_rect, action_rect)
        print(f"{p} -> {mapped}")

    # Optional: visually validate transform by moving (and optionally clicking) on the action window.
    # Safe defaults: disabled unless explicitly enabled.
    mouse_test = os.getenv('FENRIL_DUAL_MOUSE_TEST', '0') != '0'
    click_test = os.getenv('FENRIL_DUAL_CLICK_TEST', '0') != '0'
    if mouse_test:
        try:
            from src.utils.mouse import moveTo as _moveTo
            from src.utils.mouse import leftClick as _leftClick
            from src.utils.mouse import set_window_transform as _set_window_transform

            _set_window_transform(capture_rect, action_rect)

            activate_action = os.getenv('FENRIL_ACTIVATE_ACTION_WINDOW', '1') != '0'
            if activate_action:
                try:
                    if getattr(action_window, 'isMinimized', False):
                        action_window.restore()
                    action_window.activate()
                    time.sleep(0.2)
                except Exception:
                    pass

            print("=== Mouse Transform Test ===")
            print(f"enabled=True click={click_test}")
            print("Moving in 5 seconds...")
            time.sleep(5.0)

            click_all = os.getenv('FENRIL_DUAL_CLICK_ALL', '0') != '0'
            if click_test and not click_all:
                print("[safe] ClickTest will click only once (center point). Set FENRIL_DUAL_CLICK_ALL=1 to click all points.")

            test_points_local = [
                (capture_rect[2] // 2, capture_rect[3] // 2),
                (capture_rect[2] // 4, capture_rect[3] // 4),
                (max(0, capture_rect[2] - 50), 50),
            ]

            for lp in test_points_local:
                print(f"moveTo(capture_local={lp})")
                _moveTo((int(lp[0]), int(lp[1])))
                time.sleep(0.4)
                if click_test:
                    _leftClick()
                    time.sleep(0.4)
                    if not click_all:
                        break
        except Exception as e:
            print(f"Mouse test failed: {type(e).__name__}: {e}")


if __name__ == '__main__':
    main()
