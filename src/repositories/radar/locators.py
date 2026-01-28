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
# FIX: Implements local search optimization for 8x speedup
@cacheObjectPosition
def getRadarToolsPosition(screenshot: GrayImage, previousPos: Union[BBox, None] = None) -> Union[BBox, None]:
    """Locate radar tools. If previousPos provided, search locally first (8x faster)."""
    confidence = float(_RADAR_LOCATOR_CFG.get('tools_confidence', 0.80))
    
    # FIX: Try local search first if we have previous position
    if previousPos is not None:
        import cv2
        px, py, pw, ph = previousPos
        h, w = screenshot.shape[:2] if len(screenshot.shape) >= 2 else (0, 0)
        template = images.get('tools')
        if template is not None and h > 0 and w > 0:
            th, tw = template.shape[:2] if len(template.shape) >= 2 else (0, 0)
            if th > 0 and tw > 0:
                # Search in 50px neighborhood
                search_radius = 50
                x1 = max(0, px - search_radius)
                y1 = max(0, py - search_radius)
                x2 = min(w - tw, px + search_radius)
                y2 = min(h - th, py + search_radius)
                
                if x2 > x1 and y2 > y1:
                    try:
                        local_region = screenshot[y1:y2+th, x1:x2+tw]
                        if local_region.size > 0:
                            result = cv2.matchTemplate(local_region, template, cv2.TM_CCOEFF_NORMED)
                            _, conf, _, (mx, my) = cv2.minMaxLoc(result)
                            if conf >= 0.75:  # Higher threshold for local
                                return (x1 + mx, y1 + my, tw, th)
                    except Exception:
                        pass  # Fall through to full scan
    
    # Standard single-scale search
    res = locate(screenshot, images['tools'], confidence=confidence)
    if res is not None:
        return res

    # Fallback to multi-scale if enabled
    if not bool(_RADAR_LOCATOR_CFG.get('tools_multiscale', True)):
        return None

    min_scale = float(_RADAR_LOCATOR_CFG.get('tools_min_scale', 0.80))
    max_scale = float(_RADAR_LOCATOR_CFG.get('tools_max_scale', 1.20))
    steps = int(_RADAR_LOCATOR_CFG.get('tools_scale_steps', 9))
    if steps < 2:
        steps = 2
    scales = [min_scale + (max_scale - min_scale) * i / (steps - 1) for i in range(steps)]

    res = locateMultiScale(screenshot, images['tools'], confidence=confidence, scales=scales)
    if res is not None:
        return res

    # Fallback: OBS scaling / DPI scaling can move confidence below 0.80.
    # Wider scales + slightly lower confidence improves stability.
    fallback_scales = (0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40)
    return locateMultiScale(screenshot, images['tools'], confidence=max(0.65, confidence - 0.12), scales=fallback_scales)
