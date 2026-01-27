from src.repositories.radar import config
from src.shared.typings import BBox, GrayImage

import cv2
import numpy as np
import os


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
    did_trim = False
    try:
        row_std = crop.std(axis=1)
        row_mean = crop.mean(axis=1)

        # Heuristics for trimming: require the row to be both low-variance and "dark-ish"
        # (otherwise we might cut valid map rows that happen to be uniform).
        std_thr = float(os.getenv('FENRIL_RADAR_TRIM_STD_THR', '0.5'))
        mean_thr = float(os.getenv('FENRIL_RADAR_TRIM_MEAN_THR', '10.0'))
        dark_px_thr = int(os.getenv('FENRIL_RADAR_TRIM_DARK_PX_THR', '12'))
        dark_frac_thr = float(os.getenv('FENRIL_RADAR_TRIM_DARK_FRAC_THR', '0.98'))
        row_dark_frac = (crop <= dark_px_thr).mean(axis=1)

        bottom = int(crop.shape[0])
        while bottom > 1:
            i = bottom - 1
            if float(row_std[i]) > std_thr:
                break
            if float(row_mean[i]) <= mean_thr or float(row_dark_frac[i]) >= dark_frac_thr:
                bottom -= 1
                continue
            break
        if bottom != crop.shape[0]:
            crop = crop[:bottom, :]
            did_trim = True
    except Exception:
        pass

    # Optional: normalize crop back to canonical radar dimensions.
    # In practice, scaling is already handled by the tools-bbox-based crop. Resizing can
    # *hurt* matching when we trimmed a bottom black band (it stretches the map).
    try:
        target_w = int(config.dimensions['width'])
        target_h = int(config.dimensions['height'])
        normalize = os.getenv('FENRIL_RADAR_NORMALIZE_SIZE', '0').strip() in ('1', 'true', 'True')

        if normalize and not did_trim:
            dh = abs(int(crop.shape[0]) - target_h)
            dw = abs(int(crop.shape[1]) - target_w)
            # Only fix tiny rounding differences; let locateMultiScale handle the rest.
            if (dh != 0 or dw != 0) and dh <= 3 and dw <= 3:
                interp = cv2.INTER_AREA if (crop.shape[0] > target_h or crop.shape[1] > target_w) else cv2.INTER_LINEAR
                crop = cv2.resize(crop, (target_w, target_h), interpolation=interp)
    except Exception:
        pass

    return crop