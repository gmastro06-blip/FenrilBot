from typing import Optional

import pyautogui
from src.shared.typings import XYCoordinate
from .ino import sendCommandArduino

def drag(x1y1: XYCoordinate, x2y2: XYCoordinate) -> None:
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
    if sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        sendCommandArduino("leftClick")
        return
    pyautogui.leftClick(windowCoordinate[0], windowCoordinate[1])

def moveTo(windowCoordinate: XYCoordinate) -> None:
    if not sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        pyautogui.moveTo(windowCoordinate[0], windowCoordinate[1])

def rightClick(windowCoordinate: Optional[XYCoordinate] = None) -> None:
    if windowCoordinate is None:
        if not sendCommandArduino("rightClick"):
            pyautogui.rightClick()
        return
    if sendCommandArduino(f"moveTo,{int(windowCoordinate[0])},{int(windowCoordinate[1])}"):
        sendCommandArduino("rightClick")
        return
    pyautogui.rightClick(windowCoordinate[0], windowCoordinate[1])

def scroll(clicks: int) -> None:
    curX, curY = pyautogui.position()
    if not sendCommandArduino(f"scroll,{curX}, {curY}, {clicks}"):
        pyautogui.scroll(clicks)
