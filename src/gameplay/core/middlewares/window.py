import os
import re
import time
from typing import Optional

import pygetwindow as gw
import win32gui

from src.gameplay.typings import Context


_last_window_warn_time: float = 0.0


def _warn_throttled(msg: str) -> None:
    global _last_window_warn_time
    if os.getenv('FENRIL_WARN_ON_WINDOW_MISS', '0') == '0':
        return
    now = time.time()
    if now - _last_window_warn_time < 5.0:
        return
    _last_window_warn_time = now
    try:
        print(msg)
    except Exception:
        pass


def _resolve_window_exact_title(title: str) -> Optional[gw.Win32Window]:
    """Resolve a window by exact title.

    PyGetWindow's getWindowsWithTitle is substring-based; we filter to exact matches.
    """
    try:
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return None
        for w in windows:
            if getattr(w, 'title', None) == title:
                return w
        return None
    except Exception:
        return None


def _resolve_first_tibia_window() -> Optional[gw.Win32Window]:
    try:
        windowsList: list = []
        win32gui.EnumWindows(lambda hwnd, param: param.append(hwnd), windowsList)
        windowsNames = list(map(lambda hwnd: win32gui.GetWindowText(hwnd), windowsList))
        regex = re.compile(r'.*tibia.*', re.IGNORECASE)
        windowsFilter = list(filter(lambda windowName: regex.match(windowName), windowsNames))
        if len(windowsFilter) > 0:
            wins = gw.getWindowsWithTitle(windowsFilter[0])
            return wins[0] if wins else None
        return None
    except Exception:
        return None


# TODO: add unit tests
def setTibiaWindowMiddleware(context: Context) -> Context:
    # Dual-window support:
    # - capture_window: where we read pixels (e.g., OBS projector)
    # - action_window: where we send mouse/keyboard (Tibia)
    # Keep context['window'] pointing at action_window for backward compatibility.
    action_title = os.getenv('FENRIL_ACTION_WINDOW_TITLE')
    capture_title = os.getenv('FENRIL_CAPTURE_WINDOW_TITLE')

    action_exact_requested = bool(action_title)
    capture_exact_requested = bool(capture_title)
    action_exact_found = False
    capture_exact_found = False

    # Start from any pre-existing legacy window (e.g., UI-selected window).
    legacy_window = context.get('window')
    action_window = context.get('action_window') or legacy_window

    # Resolve action_window.
    if action_window is None:
        if action_title:
            action_window = _resolve_window_exact_title(action_title)
            action_exact_found = action_window is not None
            if action_exact_requested and not action_exact_found:
                _warn_throttled(f"[fenril][dual] WARN: action window title not found: {action_title!r} (falling back to Tibia regex)")
        if action_window is None:
            action_window = _resolve_first_tibia_window()

    # Resolve capture_window.
    capture_window = context.get('capture_window')
    if capture_window is None:
        if capture_title:
            capture_window = _resolve_window_exact_title(capture_title)
            capture_exact_found = capture_window is not None
            if capture_exact_requested and not capture_exact_found:
                _warn_throttled(f"[fenril][dual] WARN: capture window title not found: {capture_title!r} (falling back to action window)")
        if capture_window is None:
            capture_window = action_window

    context['action_window'] = action_window
    context['capture_window'] = capture_window
    context['window'] = action_window

    if context.get('ng_debug') is not None and isinstance(context.get('ng_debug'), dict):
        context['ng_debug']['action_window_title'] = getattr(action_window, 'title', None) if action_window else None
        context['ng_debug']['capture_window_title'] = getattr(capture_window, 'title', None) if capture_window else None
        context['ng_debug']['action_window_exact_requested'] = action_exact_requested
        context['ng_debug']['action_window_exact_found'] = action_exact_found
        context['ng_debug']['capture_window_exact_requested'] = capture_exact_requested
        context['ng_debug']['capture_window_exact_found'] = capture_exact_found
    return context
