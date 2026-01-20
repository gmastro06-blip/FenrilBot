from typing import Union

import os
from src.repositories.radar.config import images
from src.shared.typings import BBox, GrayImage
from src.utils.core import cacheObjectPosition, locate, locateMultiScale


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getRadarToolsPosition(screenshot: GrayImage) -> Union[BBox, None]:
    # OBS/projector scaling can make template matching flaky; allow tuning.
    confidence = float(os.getenv('FENRIL_RADAR_TOOLS_CONFIDENCE', '0.80'))
    res = locate(screenshot, images['tools'], confidence=confidence)
    if res is not None:
        return res

    if os.getenv('FENRIL_RADAR_TOOLS_MULTISCALE', '1') == '0':
        return None

    min_scale = float(os.getenv('FENRIL_RADAR_TOOLS_MIN_SCALE', '0.80'))
    max_scale = float(os.getenv('FENRIL_RADAR_TOOLS_MAX_SCALE', '1.20'))
    steps = int(os.getenv('FENRIL_RADAR_TOOLS_SCALE_STEPS', '9'))
    if steps < 2:
        steps = 2
    scales = [min_scale + (max_scale - min_scale) * i / (steps - 1) for i in range(steps)]
    return locateMultiScale(screenshot, images['tools'], confidence=confidence, scales=scales)
