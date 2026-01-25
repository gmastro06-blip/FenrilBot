from typing import Union

from src.utils.runtime_settings import get_bool, get_float, get_int
from src.repositories.radar.config import images
from src.shared.typings import BBox, GrayImage
from src.utils.core import cacheObjectPosition, locate, locateMultiScale


def _env_bool(name: str, default: bool) -> bool:
    return get_bool({}, '_', env_var=name, default=bool(default), prefer_env=True)


def _env_int(name: str, default: int) -> int:
    return get_int({}, '_', env_var=name, default=int(default), prefer_env=True)


def _env_float(name: str, default: float) -> float:
    return get_float({}, '_', env_var=name, default=float(default), prefer_env=True)


_RADAR_LOCATOR_CFG = {
    'tools_confidence': _env_float('FENRIL_RADAR_TOOLS_CONFIDENCE', 0.80),
    'tools_multiscale': _env_bool('FENRIL_RADAR_TOOLS_MULTISCALE', True),
    'tools_min_scale': _env_float('FENRIL_RADAR_TOOLS_MIN_SCALE', 0.80),
    'tools_max_scale': _env_float('FENRIL_RADAR_TOOLS_MAX_SCALE', 1.20),
    'tools_scale_steps': _env_int('FENRIL_RADAR_TOOLS_SCALE_STEPS', 9),
}


def configure_radar_locators(
    *,
    tools_confidence: float | None = None,
    tools_multiscale: bool | None = None,
    tools_min_scale: float | None = None,
    tools_max_scale: float | None = None,
    tools_scale_steps: int | None = None,
) -> None:
    if tools_confidence is not None:
        _RADAR_LOCATOR_CFG['tools_confidence'] = float(tools_confidence)
    if tools_multiscale is not None:
        _RADAR_LOCATOR_CFG['tools_multiscale'] = bool(tools_multiscale)
    if tools_min_scale is not None:
        _RADAR_LOCATOR_CFG['tools_min_scale'] = float(tools_min_scale)
    if tools_max_scale is not None:
        _RADAR_LOCATOR_CFG['tools_max_scale'] = float(tools_max_scale)
    if tools_scale_steps is not None:
        _RADAR_LOCATOR_CFG['tools_scale_steps'] = int(tools_scale_steps)

    # If configuration changes, clear cached locator results.
    try:
        reset_fn = getattr(getRadarToolsPosition, 'reset_cache', None)
        if callable(reset_fn):
            reset_fn()
    except Exception:
        pass


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getRadarToolsPosition(screenshot: GrayImage) -> Union[BBox, None]:
    # OBS/projector scaling can make template matching flaky; allow tuning.
    confidence = float(_RADAR_LOCATOR_CFG.get('tools_confidence', 0.80))
    res = locate(screenshot, images['tools'], confidence=confidence)
    if res is not None:
        return res

    if not bool(_RADAR_LOCATOR_CFG.get('tools_multiscale', True)):
        return None

    min_scale = float(_RADAR_LOCATOR_CFG.get('tools_min_scale', 0.80))
    max_scale = float(_RADAR_LOCATOR_CFG.get('tools_max_scale', 1.20))
    steps = int(_RADAR_LOCATOR_CFG.get('tools_scale_steps', 9))
    if steps < 2:
        steps = 2
    scales = [min_scale + (max_scale - min_scale) * i / (steps - 1) for i in range(steps)]
    return locateMultiScale(screenshot, images['tools'], confidence=confidence, scales=scales)
