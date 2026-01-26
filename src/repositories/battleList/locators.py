from typing import Union

from src.utils.runtime_settings import get_float, get_int
from src.shared.typings import BBox, GrayImage
from src.utils.core import cacheObjectPosition, locateMultiScale
from .config import images


def _env_int(name: str, default: int) -> int:
    return get_int({}, '_', env_var=name, default=int(default), prefer_env=True)


def _env_float(name: str, default: float) -> float:
    return get_float({}, '_', env_var=name, default=float(default), prefer_env=True)


_BATTLELIST_LOCATOR_CFG = {
    'icon_confidence': _env_float('FENRIL_BATTLELIST_ICON_CONFIDENCE', 0.85),
    'icon_min_scale': _env_float('FENRIL_BATTLELIST_ICON_MIN_SCALE', 0.70),
    'icon_max_scale': _env_float('FENRIL_BATTLELIST_ICON_MAX_SCALE', 1.30),
    'icon_scale_steps': _env_int('FENRIL_BATTLELIST_ICON_SCALE_STEPS', 13),
    'bottom_confidence': _env_float('FENRIL_BATTLELIST_BOTTOMBAR_CONFIDENCE', 0.85),
    'bottom_min_scale': _env_float('FENRIL_BATTLELIST_BOTTOMBAR_MIN_SCALE', 0.70),
    'bottom_max_scale': _env_float('FENRIL_BATTLELIST_BOTTOMBAR_MAX_SCALE', 1.30),
    'bottom_scale_steps': _env_int('FENRIL_BATTLELIST_BOTTOMBAR_SCALE_STEPS', 13),
}


def configure_battlelist_locators(
    *,
    icon_confidence: float | None = None,
    icon_min_scale: float | None = None,
    icon_max_scale: float | None = None,
    icon_scale_steps: int | None = None,
    bottom_confidence: float | None = None,
    bottom_min_scale: float | None = None,
    bottom_max_scale: float | None = None,
    bottom_scale_steps: int | None = None,
) -> None:
    if icon_confidence is not None:
        _BATTLELIST_LOCATOR_CFG['icon_confidence'] = float(icon_confidence)
    if icon_min_scale is not None:
        _BATTLELIST_LOCATOR_CFG['icon_min_scale'] = float(icon_min_scale)
    if icon_max_scale is not None:
        _BATTLELIST_LOCATOR_CFG['icon_max_scale'] = float(icon_max_scale)
    if icon_scale_steps is not None:
        _BATTLELIST_LOCATOR_CFG['icon_scale_steps'] = int(icon_scale_steps)
    if bottom_confidence is not None:
        _BATTLELIST_LOCATOR_CFG['bottom_confidence'] = float(bottom_confidence)
    if bottom_min_scale is not None:
        _BATTLELIST_LOCATOR_CFG['bottom_min_scale'] = float(bottom_min_scale)
    if bottom_max_scale is not None:
        _BATTLELIST_LOCATOR_CFG['bottom_max_scale'] = float(bottom_max_scale)
    if bottom_scale_steps is not None:
        _BATTLELIST_LOCATOR_CFG['bottom_scale_steps'] = int(bottom_scale_steps)

    # If configuration changes, clear cached locator results.
    try:
        reset_fn = getattr(getBattleListIconPosition, 'reset_cache', None)
        if callable(reset_fn):
            reset_fn()
    except Exception:
        pass
    try:
        reset_fn = getattr(getContainerBottomBarPosition, 'reset_cache', None)
        if callable(reset_fn):
            reset_fn()
    except Exception:
        pass


# PERF: [0.05150189999999988, 2.000000000279556e-06]
@cacheObjectPosition
def getBattleListIconPosition(screenshot: GrayImage) -> Union[BBox, None]:
    confidence = float(_BATTLELIST_LOCATOR_CFG.get('icon_confidence', 0.85))
    min_scale = float(_BATTLELIST_LOCATOR_CFG.get('icon_min_scale', 0.70))
    max_scale = float(_BATTLELIST_LOCATOR_CFG.get('icon_max_scale', 1.30))
    steps = int(_BATTLELIST_LOCATOR_CFG.get('icon_scale_steps', 13))
    if steps < 2:
        steps = 2
    scales = [min_scale + (max_scale - min_scale) * i / (steps - 1) for i in range(steps)]
    res = locateMultiScale(screenshot, images['icons']['ng_battleList'], confidence=confidence, scales=scales)
    if res is not None:
        return res

    # Fallback for OBS/projector scaling and slight theme differences.
    # Keep this inside the locator so callers don't need to tune env vars.
    fallback_scales = (0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80)
    return locateMultiScale(screenshot, images['icons']['ng_battleList'], confidence=max(0.60, confidence - 0.15), scales=fallback_scales)


# PERF: [0.05364349999999973, 1.8999999991109462e-06]
@cacheObjectPosition
def getContainerBottomBarPosition(screenshot: GrayImage) -> Union[BBox, None]:
    confidence = float(_BATTLELIST_LOCATOR_CFG.get('bottom_confidence', 0.85))
    min_scale = float(_BATTLELIST_LOCATOR_CFG.get('bottom_min_scale', 0.70))
    max_scale = float(_BATTLELIST_LOCATOR_CFG.get('bottom_max_scale', 1.30))
    steps = int(_BATTLELIST_LOCATOR_CFG.get('bottom_scale_steps', 13))
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

    res = locateMultiScale(screenshot, images['containers']['bottomBar'], confidence=confidence, scales=scales)
    if res is not None:
        return res

    # Fallback for scaled captures.
    fallback_scales = (0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50, 1.60, 1.70, 1.80)
    return locateMultiScale(screenshot, images['containers']['bottomBar'], confidence=max(0.60, confidence - 0.15), scales=fallback_scales)
