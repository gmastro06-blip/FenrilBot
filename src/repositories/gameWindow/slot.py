from typing import Tuple

from src.shared.typings import BBox, Slot
from src.utils.mouse import leftClick, moveTo, rightClick

# TODO: add unit tests
# TODO: add perf
def getSlotPosition(slot: Slot, gameWindowPosition: BBox) -> Tuple[int, int]:
    (gameWindowPositionX, gameWindowPositionY, gameWindowWidth, gameWindowHeight) = gameWindowPosition
    (slotX, slotY) = slot
    slotHeight = gameWindowHeight // 11
    slotWidth = gameWindowWidth // 15
    slotXCoordinate = gameWindowPositionX + (slotX * slotWidth)
    slotYCoordinate = gameWindowPositionY + (slotY * slotHeight)
    return (slotXCoordinate + 32, slotYCoordinate + 32)

# TODO: add unit tests
# TODO: add perf
def moveToSlot(slot: Slot, gameWindowPosition: BBox) -> None:
    slotPosition = getSlotPosition(slot, gameWindowPosition)
    moveTo(slotPosition)

# TODO: add unit tests
# TODO: add perf
def clickSlot(slot: Slot, gameWindowPosition: BBox) -> None:
    slotPosition = getSlotPosition(slot, gameWindowPosition)
    leftClick(slotPosition)

# TODO: add unit tests
# TODO: add perf
def rightClickSlot(slot: Slot, gameWindowPosition: BBox) -> None:
    slotPosition = getSlotPosition(slot, gameWindowPosition)
    rightClick(slotPosition)

def clickUseBySlot(slot: Slot, gameWindowPosition: BBox) -> None:
    (gameWindowPositionX, gameWindowPositionY, gameWindowWidth, gameWindowHeight) = gameWindowPosition
    slotWidth = gameWindowWidth // 15
    slotHeight = gameWindowHeight // 11
    
    # ERROR 3: Offset relativo al tamaño del slot (aprox 1/4 hacia el centro)
    # Esto escala correctamente entre 720p (32px) y 1080p (64px)
    offset_x = max(8, slotWidth // 4)
    offset_y = max(12, slotHeight // 3)
    
    xPos, yPos = getSlotPosition(slot, gameWindowPosition)
    leftClick((xPos + offset_x, yPos + offset_y))