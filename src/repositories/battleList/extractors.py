from numba import njit
import numpy as np
from typing import Union
from src.shared.typings import GrayImage, XYCoordinate
from .locators import getContainerBottomBarPosition, getBattleListIconPosition
from src.utils.runtime_settings import get_int


def _env_int(name: str, default: int) -> int:
    return get_int({}, '_', env_var=name, default=int(default), prefer_env=True)


_BATTLELIST_EXTRACTOR_CFG = {
    'click_x_offset': _env_int('FENRIL_BATTLELIST_CLICK_X_OFFSET', 60),
}


def configure_battlelist_extractors(*, click_x_offset: int | None = None) -> None:
    if click_x_offset is not None:
        _BATTLELIST_EXTRACTOR_CFG['click_x_offset'] = int(click_x_offset)


# PERF: [0.05485419999999941, 4.39999999990448e-06]
def getContent(screenshot: GrayImage) -> Union[GrayImage, None]:
    battleListIconPosition = getBattleListIconPosition(screenshot)
    if battleListIconPosition is None:
        return None
    content = screenshot[battleListIconPosition[1] + battleListIconPosition[3] +
                         1:, battleListIconPosition[0] - 1:battleListIconPosition[0] - 1 + 156]
    containerBottomBarPos = getContainerBottomBarPosition(content)
    if containerBottomBarPos is None:
        return None
    return content[:containerBottomBarPos[1] - 11, :]

def getCreatureClickCoordinate(screenshot: GrayImage, *, index: int = 0) -> Union[XYCoordinate, None]:
    """Return a capture-local coordinate to click the given battle list row.

    This is used as a fallback when on-screen creature clicking is not available.
    """

    if screenshot is None or index < 0:
        return None

    battleListIconPosition = getBattleListIconPosition(screenshot)
    if battleListIconPosition is None:
        return None

    # Match the slicing logic in getContent().
    list_left = battleListIconPosition[0] - 1
    list_top = battleListIconPosition[1] + battleListIconPosition[3] + 1

    # Row layout (based on extractors/core constants):
    # - each entry is 22px tall
    # - first entry starts after an 11px header
    row_height = 22
    header_height = 11

    # Click somewhere inside the name area (avoid the scrollbar on the right).
    x_offset = int(_BATTLELIST_EXTRACTOR_CFG.get('click_x_offset', 60))
    click_x = int(list_left + x_offset)
    click_y = int(list_top + header_height + (index * row_height) + (row_height // 2))

    if click_x < 0 or click_y < 0:
        return None
    if click_x >= screenshot.shape[1] or click_y >= screenshot.shape[0]:
        return None

    return (click_x, click_y)


# PERF: [0.8151709999999994, 1.1999999999900979e-05]
# TODO: add unit tests
@njit(cache=True, fastmath=True, boundscheck=False)
def getCreaturesNamesImages(content: GrayImage, filledSlotsCount: int) -> GrayImage:
    creaturesNamesImages = np.zeros((filledSlotsCount, 115), dtype=np.uint8)
    for i in range(filledSlotsCount):
        y = 11 + (i * 22)
        creatureNameImage = content[y:y + 1, 23:138][0]

        # The original implementation relied on exact pixel values (192/247),
        # which breaks on different Tibia themes / capture gamma.
        # We canonicalize each name row into a binary-ish mask where "text"
        # pixels become 192 and background remains 0.
        min_v = 255
        max_v = 0
        for j in range(creatureNameImage.shape[0]):
            v = creatureNameImage[j]
            if v < min_v:
                min_v = v
            if v > max_v:
                max_v = v

        for j in range(creatureNameImage.shape[0]):
            v = creatureNameImage[j]
            if v == 192 or v == 247:
                creaturesNamesImages[i, j] = 192
            elif max_v < 120:
                # Dark theme: text is only slightly brighter than background.
                if v >= min_v + 10:
                    creaturesNamesImages[i, j] = 192
            else:
                # Light theme or high-contrast capture: keep a conservative threshold.
                if v >= 170:
                    creaturesNamesImages[i, j] = 192
    return creaturesNamesImages
