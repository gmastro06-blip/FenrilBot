from src.repositories.radar import config
from src.shared.typings import BBox, GrayImage

import cv2


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


# TODO: add unit tests
# TODO: add perf
def getRadarImage(screenshot: GrayImage, radarToolsPosition: BBox) -> GrayImage:
    # The radar crop is positioned relative to the "radar tools" icon.
    # When using OBS projector or Windows DPI scaling, the capture can be scaled.
    # Use the matched tools bbox size to infer scale and normalize the crop back
    # to canonical radar dimensions.
    try:
        tpl_h, tpl_w = config.images['tools'].shape[:2]
        _, _, found_w, found_h = radarToolsPosition
        scale_x = float(found_w) / float(tpl_w) if tpl_w else 1.0
        scale_y = float(found_h) / float(tpl_h) if tpl_h else 1.0
        scale = (scale_x + scale_y) / 2.0
        if scale <= 0:
            scale = 1.0
    except Exception:
        scale = 1.0

    base_w = int(config.dimensions['width'])
    base_h = int(config.dimensions['height'])
    w = max(1, int(round(base_w * scale)))
    h = max(1, int(round(base_h * scale)))
    dx = int(round(11 * scale))
    dy = int(round(50 * scale))

    x0 = int(radarToolsPosition[0]) - w - dx
    y0 = int(radarToolsPosition[1]) - dy
    x1 = x0 + w
    y1 = y0 + h

    # Clamp to screenshot bounds.
    img_h, img_w = screenshot.shape[:2]
    x0c = _clamp(x0, 0, img_w)
    x1c = _clamp(x1, 0, img_w)
    y0c = _clamp(y0, 0, img_h)
    y1c = _clamp(y1, 0, img_h)

    crop = screenshot[y0c:y1c, x0c:x1c]
    if crop.size == 0:
        return crop

    # Some UI layouts/minimap sizes include a non-map band at the bottom of this crop
    # (often pure black). Trim trailing rows with near-zero variance so matching doesn't fail.
    try:
        row_std = crop.std(axis=1)
        thr = 0.5
        bottom = int(crop.shape[0])
        while bottom > 1 and float(row_std[bottom - 1]) <= thr:
            bottom -= 1
        if bottom != crop.shape[0]:
            crop = crop[:bottom, :]
    except Exception:
        pass

    # Normalize crop back to canonical radar dimensions so matching is consistent.
    # This addresses OBS projector scaling / Windows DPI scaling. (Not minimap zoom.)
    try:
        target_w = int(config.dimensions['width'])
        target_h = int(config.dimensions['height'])
        if crop.shape[0] != target_h or crop.shape[1] != target_w:
            interp = cv2.INTER_AREA if (crop.shape[0] > target_h or crop.shape[1] > target_w) else cv2.INTER_LINEAR
            crop = cv2.resize(crop, (target_w, target_h), interpolation=interp)
    except Exception:
        pass

    return crop