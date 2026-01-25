from typing import Optional, Tuple

import time

import pyautogui
from src.shared.typings import XYCoordinate
from .ino import sendCommandArduino
from src.utils.runtime_settings import get_bool


_capture_rect: Optional[Tuple[int, int, int, int]] = None
_action_rect: Optional[Tuple[int, int, int, int]] = None

_last_click_diag_time: float = 0.0
_last_click_backend: Optional[str] = None

_INPUT_DIAG_ENABLED: bool = get_bool({}, '_', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True)
_DISABLE_ARDUINO_CLICKS: bool = get_bool({}, '_', env_var='FENRIL_DISABLE_ARDUINO_CLICKS', default=False, prefer_env=True)


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
) -> None:
    """Set a coordinate transform from capture-local coords -> action absolute coords.

    Rect format is (left, top, width, height) in absolute screen coordinates.
    When not set (or invalid), behavior is identity.
    """
    global _capture_rect, _action_rect
    _capture_rect = capture_rect
    _action_rect = action_rect


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
    windowCoordinate = _transform_capture_to_action(windowCoordinate)
    if not sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        pyautogui.moveTo(windowCoordinate[0], windowCoordinate[1])

def rightClick(windowCoordinate: Optional[XYCoordinate] = None) -> None:
    global _last_click_backend
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
    curX, curY = pyautogui.position()
    if not sendCommandArduino(f"scroll,{curX}, {curY}, {clicks}"):
        pyautogui.scroll(clicks)
