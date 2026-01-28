from typing import Optional, Tuple

import time

import pyautogui
from src.shared.typings import XYCoordinate
from .ino import sendCommandArduino
from src.utils.runtime_settings import get_bool, get_int


_capture_rect: Optional[Tuple[int, int, int, int]] = None
_action_rect: Optional[Tuple[int, int, int, int]] = None
_action_hwnd: Optional[int] = None
_action_title: Optional[str] = None
_action_rect_is_client: bool = False

_last_focus_attempt_time: float = 0.0

_last_click_diag_time: float = 0.0
_last_click_backend: Optional[str] = None

_INPUT_DIAG_ENABLED: bool = get_bool({}, '_', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True)
_DISABLE_ARDUINO_CLICKS: bool = get_bool({}, '_', env_var='FENRIL_DISABLE_ARDUINO_CLICKS', default=False, prefer_env=True)
_DISABLE_INPUT: bool = get_bool({}, '_', env_var='FENRIL_DISABLE_INPUT', default=False, prefer_env=True)


def configure_mouse(*, input_diag: Optional[bool] = None, disable_arduino_clicks: Optional[bool] = None) -> None:
    global _INPUT_DIAG_ENABLED, _DISABLE_ARDUINO_CLICKS
    if input_diag is not None:
        _INPUT_DIAG_ENABLED = bool(input_diag)
    if disable_arduino_clicks is not None:
        _DISABLE_ARDUINO_CLICKS = bool(disable_arduino_clicks)


def _click_diag(msg: str) -> None:
    global _last_click_diag_time
    if not _INPUT_DIAG_ENABLED:
        return
    now = time.time()
    if now - _last_click_diag_time < 0.5:
        return
    _last_click_diag_time = now
    try:
        print(msg)
    except Exception:
        pass


def get_last_click_backend() -> Optional[str]:
    """Return the backend used by the last click: 'arduino' or 'pyautogui'."""
    return _last_click_backend


def set_window_transform(
    capture_rect: Optional[Tuple[int, int, int, int]],
    action_rect: Optional[Tuple[int, int, int, int]],
    action_hwnd: Optional[int] = None,
    action_title: Optional[str] = None,
    action_rect_is_client: Optional[bool] = None,
) -> None:
    """Set a coordinate transform from capture-local coords -> action absolute coords.

    Rect format is (left, top, width, height) in absolute screen coordinates.
    When not set (or invalid), behavior is identity.
    """
    global _capture_rect, _action_rect, _action_hwnd, _action_title, _action_rect_is_client
    _capture_rect = capture_rect
    _action_rect = action_rect
    _action_hwnd = int(action_hwnd) if action_hwnd is not None else None
    _action_title = str(action_title) if action_title else None
    if action_rect_is_client is not None:
        _action_rect_is_client = bool(action_rect_is_client)


def _point_in_action_rect(coord: XYCoordinate) -> bool:
    if _action_rect is None:
        return True
    left, top, w, h = _action_rect
    if w <= 0 or h <= 0:
        return False
    # Default top-guard is only aggressive when action_rect might include window chrome.
    default_top_guard = 2 if _action_rect_is_client else 14
    border_guard = get_int({}, '_', env_var='FENRIL_ACTION_BORDER_GUARD_PX', default=2, prefer_env=True)
    top_guard = get_int({}, '_', env_var='FENRIL_ACTION_TOP_GUARD_PX', default=default_top_guard, prefer_env=True)
    if border_guard < 0:
        border_guard = 0
    if top_guard < 0:
        top_guard = 0
    x, y = int(coord[0]), int(coord[1])
    inner_left = left + border_guard
    inner_right = (left + w) - border_guard
    inner_top = top + max(border_guard, top_guard)
    inner_bottom = (top + h) - border_guard
    if inner_right <= inner_left or inner_bottom <= inner_top:
        return False
    return (inner_left <= x < inner_right) and (inner_top <= y < inner_bottom)


def _ensure_action_window_focused() -> bool:
    """Best-effort: focus the action window (Tibia) to avoid clicking VS Code."""
    global _last_focus_attempt_time

    require_focus = get_bool({}, '_', env_var='FENRIL_REQUIRE_ACTION_FOCUS', default=True, prefer_env=True)
    if not require_focus:
        return True

    if _action_hwnd is None:
        # Without a handle, we cannot reliably ensure focus.
        return False

    try:
        import win32gui
        import win32con

        fg = win32gui.GetForegroundWindow()
        if fg == _action_hwnd:
            return True

        now = time.time()
        # Avoid hammering SetForegroundWindow.
        if now - _last_focus_attempt_time < 0.5:
            return False
        _last_focus_attempt_time = now

        # Do NOT restore/unmaximize unless minimized.
        try:
            if win32gui.IsIconic(_action_hwnd):
                win32gui.ShowWindow(_action_hwnd, win32con.SW_RESTORE)
        except Exception:
            pass
        try:
            win32gui.BringWindowToTop(_action_hwnd)
        except Exception:
            pass
        try:
            win32gui.SetForegroundWindow(_action_hwnd)
        except Exception:
            pass

        # Re-check.
        fg2 = win32gui.GetForegroundWindow()
        return fg2 == _action_hwnd
    except Exception:
        return False


def _should_block_click(coord: Optional[XYCoordinate]) -> bool:
    if _DISABLE_INPUT:
        _click_diag(f"[fenril][input] BLOCK input disabled (FENRIL_DISABLE_INPUT=1) title={_action_title!r}")
        return True
    # If we are clicking at cursor, require focus.
    if coord is None:
        # Retry logic: 2 attempts with 50ms delay to reduce race conditions
        for attempt in range(2):
            ok = _ensure_action_window_focused()
            if ok:
                return False
            if attempt < 1:
                try:
                    time.sleep(0.05)
                except Exception:
                    pass
        _click_diag(f"[fenril][input] BLOCK click-at-cursor (focus failed after 2 retries) title={_action_title!r}")
        return True

    abs_coord = _transform_capture_to_action(coord)
    if not _point_in_action_rect(abs_coord):
        _click_diag(
            f"[fenril][input] BLOCK click outside action_rect coord={abs_coord} action_rect={_action_rect} title={_action_title!r}"
        )
        return True

    # Retry logic: 2 attempts with 50ms delay to reduce race conditions
    for attempt in range(2):
        ok = _ensure_action_window_focused()
        if ok:
            return False
        if attempt < 1:
            try:
                time.sleep(0.05)
            except Exception:
                pass
    _click_diag(
        f"[fenril][input] BLOCK click (focus failed after 2 retries) coord={abs_coord} title={_action_title!r}"
    )
    return True


def _transform_capture_to_action(coord: XYCoordinate) -> XYCoordinate:
    if _capture_rect is None or _action_rect is None:
        return coord

    cap_left, cap_top, cap_w, cap_h = _capture_rect
    act_left, act_top, act_w, act_h = _action_rect

    if cap_w <= 0 or cap_h <= 0 or act_w <= 0 or act_h <= 0:
        return coord

    x, y = int(coord[0]), int(coord[1])

    # Safety: only transform coords that look like they are in capture-local space.
    # If the caller already passes absolute coordinates, leave them untouched.
    if x < 0 or y < 0 or x > cap_w or y > cap_h:
        return coord

    ax = act_left + (x * act_w / cap_w)
    ay = act_top + (y * act_h / cap_h)
    return (int(round(ax)), int(round(ay)))


def transform_capture_to_action(coord: XYCoordinate) -> XYCoordinate:
    """Public wrapper used for diagnostics/logging."""
    return _transform_capture_to_action(coord)


def get_window_transform() -> tuple[Optional[Tuple[int, int, int, int]], Optional[Tuple[int, int, int, int]]]:
    """Return (capture_rect, action_rect) currently used for coordinate transform."""
    return (_capture_rect, _action_rect)

def drag(x1y1: XYCoordinate, x2y2: XYCoordinate) -> None:
    if _should_block_click(x1y1) or _should_block_click(x2y2):
        return
    x1y1 = _transform_capture_to_action(x1y1)
    x2y2 = _transform_capture_to_action(x2y2)
    if sendCommandArduino(f"moveTo,{int(x1y1[0])},{int(x1y1[1])}"):
        sendCommandArduino("dragStart")
        sendCommandArduino(f"moveTo,{int(x2y2[0])},{int(x2y2[1])}")
        sendCommandArduino("dragEnd")
        return

    pyautogui.moveTo(x1y1[0], x1y1[1])
    pyautogui.dragTo(x2y2[0], x2y2[1], button="left")

def leftClick(windowCoordinate: Optional[XYCoordinate] = None) -> None:
    global _last_click_backend
    if _should_block_click(windowCoordinate):
        return
    disable_arduino_clicks = _DISABLE_ARDUINO_CLICKS
    if windowCoordinate is None:
        used_arduino = sendCommandArduino("leftClick")
        if not used_arduino:
            pyautogui.leftClick()
        _last_click_backend = 'arduino' if used_arduino else 'pyautogui'
        _click_diag(f"[fenril][input] leftClick backend={'arduino' if used_arduino else 'pyautogui'} coord=None")
        return
    windowCoordinate = _transform_capture_to_action(windowCoordinate)

    # If we are forcing pyautogui clicks, don't issue Arduino move commands either.
    # Some firmwares smooth movement and can cause the cursor to drift during the click.
    if disable_arduino_clicks:
        pyautogui.leftClick(windowCoordinate[0], windowCoordinate[1])
        _last_click_backend = 'pyautogui'
        _click_diag(f"[fenril][input] leftClick backend=pyautogui coord={windowCoordinate}")
        return

    if sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        used_arduino = sendCommandArduino("leftClick")
        _last_click_backend = 'arduino' if used_arduino else 'pyautogui'
        _click_diag(f"[fenril][input] leftClick backend={'arduino' if used_arduino else 'pyautogui'} coord={windowCoordinate}")
        if not used_arduino:
            pyautogui.leftClick(windowCoordinate[0], windowCoordinate[1])
        return
    pyautogui.leftClick(windowCoordinate[0], windowCoordinate[1])
    _last_click_backend = 'pyautogui'
    _click_diag(f"[fenril][input] leftClick backend=pyautogui coord={windowCoordinate}")

def moveTo(windowCoordinate: XYCoordinate) -> None:
    if _DISABLE_INPUT:
        _click_diag(f"[fenril][input] BLOCK moveTo (input disabled) title={_action_title!r}")
        return
    # Allow moving even when the action window isn't focused.
    # Reason: some call sites use "click-at-cursor" flows (move first, then click(None)).
    # If we block the move due to focus but later manage to focus and allow the click,
    # the click will happen at a stale cursor position (often on taskbar/VS Code),
    # which can minimize the client or spam-click the editor.
    windowCoordinate = _transform_capture_to_action(windowCoordinate)
    if not _point_in_action_rect(windowCoordinate):
        _click_diag(
            f"[fenril][input] BLOCK moveTo outside action_rect coord={windowCoordinate} action_rect={_action_rect} title={_action_title!r}"
        )
        return
    if not sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        pyautogui.moveTo(windowCoordinate[0], windowCoordinate[1])

def rightClick(windowCoordinate: Optional[XYCoordinate] = None) -> None:
    global _last_click_backend
    if _should_block_click(windowCoordinate):
        return
    disable_arduino_clicks = _DISABLE_ARDUINO_CLICKS
    if windowCoordinate is None:
        used_arduino = sendCommandArduino("rightClick")
        if not used_arduino:
            pyautogui.rightClick()
        _last_click_backend = 'arduino' if used_arduino else 'pyautogui'
        _click_diag(f"[fenril][input] rightClick backend={'arduino' if used_arduino else 'pyautogui'} coord=None")
        return
    windowCoordinate = _transform_capture_to_action(windowCoordinate)

    if disable_arduino_clicks:
        pyautogui.rightClick(windowCoordinate[0], windowCoordinate[1])
        _last_click_backend = 'pyautogui'
        _click_diag(f"[fenril][input] rightClick backend=pyautogui coord={windowCoordinate}")
        return

    if sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        used_arduino = sendCommandArduino("rightClick")
        _last_click_backend = 'arduino' if used_arduino else 'pyautogui'
        _click_diag(f"[fenril][input] rightClick backend={'arduino' if used_arduino else 'pyautogui'} coord={windowCoordinate}")
        if not used_arduino:
            pyautogui.rightClick(windowCoordinate[0], windowCoordinate[1])
        return
    pyautogui.rightClick(windowCoordinate[0], windowCoordinate[1])
    _last_click_backend = 'pyautogui'
    _click_diag(f"[fenril][input] rightClick backend=pyautogui coord={windowCoordinate}")

def scroll(clicks: int) -> None:
    if _DISABLE_INPUT:
        _click_diag(f"[fenril][input] BLOCK scroll (input disabled) title={_action_title!r}")
        return
    # Scrolling can also affect the wrong window.
    if _should_block_click(None):
        return
    curX, curY = pyautogui.position()
    if not sendCommandArduino(f"scroll,{curX}, {curY}, {clicks}"):
        pyautogui.scroll(clicks)
