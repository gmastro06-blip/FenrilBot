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
    xPos, yPos = getSlotPosition(slot, gameWindowPosition)
    leftClick((xPos + 15, yPos + 25))