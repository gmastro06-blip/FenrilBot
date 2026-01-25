import re
import time
from typing import Optional

import pygetwindow as gw
import win32gui

from src.gameplay.typings import Context
from src.utils.runtime_settings import get_bool, get_str


_last_window_warn_time: float = 0.0


def _warn_throttled(context: Context, msg: str) -> None:
    global _last_window_warn_time
    if not get_bool(context, 'ng_runtime.warn_on_window_miss', env_var='FENRIL_WARN_ON_WINDOW_MISS', default=False):
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


def _resolve_window_fuzzy_title(title: str) -> Optional[gw.Win32Window]:
    """Resolve a window by title, preferring exact match but allowing substring.

    This makes env vars like FENRIL_CAPTURE_WINDOW_TITLE resilient to minor title
    changes (OBS version/profile text, localization) and allows users to pass a
    stable substring (e.g. "Proyector en ventana").
    """
    win = _resolve_window_exact_title(title)
    if win is not None:
        return win
    try:
        wins = gw.getWindowsWithTitle(title)
        return wins[0] if wins else None
    except Exception:
        return None


def _resolve_first_tibia_window() -> Optional[gw.Win32Window]:
    try:
        windowsList: list = []
        win32gui.EnumWindows(lambda hwnd, param: param.append(hwnd), windowsList)
        windowsNames = list(map(lambda hwnd: win32gui.GetWindowText(hwnd), windowsList))
        regex = re.compile(r'.*tibia.*', re.IGNORECASE)
        candidates = [name for name in windowsNames if name and regex.match(name)]
        if not candidates:
            return None

        # Avoid selecting OBS projector / OBS UI as the "action" window.
        def is_bad(title: str) -> bool:
            t = title.lower()
            return (
                'proyector en ventana' in t
                or 'projector' in t
                or t.startswith('obs')
                or 'obs ' in t
            )

        filtered = [t for t in candidates if not is_bad(t)]

        # Prefer the common Tibia client title format when available.
        preferred = [t for t in filtered if t.lower().startswith('tibia -')]
        pick = (preferred[0] if preferred else (filtered[0] if filtered else candidates[0]))

        wins = gw.getWindowsWithTitle(pick)
        return wins[0] if wins else None
        return None
    except Exception:
        return None


def _resolve_default_capture_window() -> Optional[gw.Win32Window]:
    """Try to pick a sensible default capture window.

    In many setups, users capture from an OBS projector window rather than the
    Tibia client directly. Prefer that when available.
    """
    for hint in (
        'Proyector en ventana',  # OBS Spanish
        'Projector',             # OBS English
    ):
        try:
            wins = gw.getWindowsWithTitle(hint)
            if wins:
                return wins[0]
        except Exception:
            continue
    return None


# TODO: add unit tests
def setTibiaWindowMiddleware(context: Context) -> Context:
    # Dual-window support:
    # - capture_window: where we read pixels (e.g., OBS projector)
    # - action_window: where we send mouse/keyboard (Tibia)
    # Keep context['window'] pointing at action_window for backward compatibility.
    action_title = get_str(context, 'ng_runtime.action_window_title', env_var='FENRIL_ACTION_WINDOW_TITLE', default='').strip() or None
    capture_title = get_str(context, 'ng_runtime.capture_window_title', env_var='FENRIL_CAPTURE_WINDOW_TITLE', default='').strip() or None

    # Structured window info for diagnostics/timeouts.
    ng_window = context.get('ng_window') if isinstance(context.get('ng_window'), dict) else {}
    ng_window['action_title'] = action_title
    ng_window['capture_title'] = capture_title

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
            action_window = _resolve_window_fuzzy_title(action_title)
            action_exact_found = action_window is not None
            if action_exact_requested and not action_exact_found:
                _warn_throttled(context, f"[fenril][dual] WARN: action window title not found: {action_title!r} (falling back to Tibia regex)")
        if action_window is None:
            action_window = _resolve_first_tibia_window()

    # Resolve capture_window.
    capture_window = context.get('capture_window')
    if capture_window is None:
        if capture_title:
            capture_window = _resolve_window_fuzzy_title(capture_title)
            capture_exact_found = capture_window is not None
            if capture_exact_requested and not capture_exact_found:
                _warn_throttled(context, f"[fenril][dual] WARN: capture window title not found: {capture_title!r} (falling back to action window)")
        if capture_window is None and not capture_title:
            capture_window = _resolve_default_capture_window()
        if capture_window is None:
            capture_window = action_window

    context['action_window'] = action_window
    context['capture_window'] = capture_window
    context['window'] = action_window

    try:
        ng_window['action_resolved_title'] = getattr(action_window, 'title', None) if action_window else None
        ng_window['capture_resolved_title'] = getattr(capture_window, 'title', None) if capture_window else None
    except Exception:
        pass
    context['ng_window'] = ng_window

    if context.get('ng_debug') is not None and isinstance(context.get('ng_debug'), dict):
        context['ng_debug']['action_window_title'] = getattr(action_window, 'title', None) if action_window else None
        context['ng_debug']['capture_window_title'] = getattr(capture_window, 'title', None) if capture_window else None
        context['ng_debug']['action_window_exact_requested'] = action_exact_requested
        context['ng_debug']['action_window_exact_found'] = action_exact_found
        context['ng_debug']['capture_window_exact_requested'] = capture_exact_requested
        context['ng_debug']['capture_window_exact_found'] = capture_exact_found
    return context
