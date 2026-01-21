import os
from typing import Union
from src.shared.typings import BBox, GrayImage
from src.utils.core import cacheObjectPosition, locateMultiScale
from .config import images


# PERF: [0.05150189999999988, 2.000000000279556e-06]
@cacheObjectPosition
def getBattleListIconPosition(screenshot: GrayImage) -> Union[BBox, None]:
    confidence = float(os.getenv('FENRIL_BATTLELIST_ICON_CONFIDENCE', '0.85'))
    min_scale = float(os.getenv('FENRIL_BATTLELIST_ICON_MIN_SCALE', '0.70'))
    max_scale = float(os.getenv('FENRIL_BATTLELIST_ICON_MAX_SCALE', '1.30'))
    steps = int(os.getenv('FENRIL_BATTLELIST_ICON_SCALE_STEPS', '13'))
    if steps < 2:
        steps = 2
    scales = [min_scale + (max_scale - min_scale) * i / (steps - 1) for i in range(steps)]
    return locateMultiScale(screenshot, images['icons']['ng_battleList'], confidence=confidence, scales=scales)


# PERF: [0.05364349999999973, 1.8999999991109462e-06]
@cacheObjectPosition
def getContainerBottomBarPosition(screenshot: GrayImage) -> Union[BBox, None]:
    confidence = float(os.getenv('FENRIL_BATTLELIST_BOTTOMBAR_CONFIDENCE', '0.85'))
    min_scale = float(os.getenv('FENRIL_BATTLELIST_BOTTOMBAR_MIN_SCALE', '0.70'))
    max_scale = float(os.getenv('FENRIL_BATTLELIST_BOTTOMBAR_MAX_SCALE', '1.30'))
    steps = int(os.getenv('FENRIL_BATTLELIST_BOTTOMBAR_SCALE_STEPS', '13'))
    if steps < 2:
        steps = 2
    scales = [min_scale + (max_scale - min_scale) * i / (steps - 1) for i in range(steps)]

    iconPosition = locateMultiScale(screenshot, images['icons']['ng_battleList'], confidence=confidence, scales=scales)
    if iconPosition is not None:
        start_x = max(0, iconPosition[0] - 50)
        start_y = max(0, iconPosition[1])
        end_x = min(screenshot.shape[1], start_x + 500)
        end_y = min(screenshot.shape[0], start_y + 800)
        cropped = screenshot[start_y:end_y, start_x:end_x]
        position = locateMultiScale(cropped, images['containers']['bottomBar'], confidence=confidence, scales=scales)
        if position is not None:
            return (position[0] + start_x, position[1] + start_y, position[2], position[3])

    return locateMultiScale(screenshot, images['containers']['bottomBar'], confidence=confidence, scales=scales)
