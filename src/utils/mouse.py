from typing import Optional, Tuple

import pyautogui
from src.shared.typings import XYCoordinate
from .ino import sendCommandArduino


_capture_rect: Optional[Tuple[int, int, int, int]] = None
_action_rect: Optional[Tuple[int, int, int, int]] = None


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
    if windowCoordinate is None:
        if not sendCommandArduino("leftClick"):
            pyautogui.leftClick()
        return
    windowCoordinate = _transform_capture_to_action(windowCoordinate)
    if sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        sendCommandArduino("leftClick")
        return
    pyautogui.leftClick(windowCoordinate[0], windowCoordinate[1])

def moveTo(windowCoordinate: XYCoordinate) -> None:
    windowCoordinate = _transform_capture_to_action(windowCoordinate)
    if not sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        pyautogui.moveTo(windowCoordinate[0], windowCoordinate[1])

def rightClick(windowCoordinate: Optional[XYCoordinate] = None) -> None:
    if windowCoordinate is None:
        if not sendCommandArduino("rightClick"):
            pyautogui.rightClick()
        return
    windowCoordinate = _transform_capture_to_action(windowCoordinate)
    if sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        sendCommandArduino("rightClick")
        return
    pyautogui.rightClick(windowCoordinate[0], windowCoordinate[1])

def scroll(clicks: int) -> None:
    curX, curY = pyautogui.position()
    if not sendCommandArduino(f"scroll,{curX}, {curY}, {clicks}"):
        pyautogui.scroll(clicks)
