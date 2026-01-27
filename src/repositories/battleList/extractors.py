from numba import njit
import numpy as np
from typing import Union
from src.shared.typings import GrayImage, XYCoordinate
from .locators import getContainerBottomBarPosition, getBattleListIconPosition
from src.utils.runtime_settings import get_int
import cv2
from src.utils.core import locateMultiScale
from .config import images


def _env_int(name: str, default: int) -> int:
    return get_int({}, '_', env_var=name, default=int(default), prefer_env=True)


_BATTLELIST_EXTRACTOR_CFG = {
    'click_x_offset': _env_int('FENRIL_BATTLELIST_CLICK_X_OFFSET', 60),
}


def configure_battlelist_extractors(*, click_x_offset: int | None = None) -> None:
    if click_x_offset is not None:
        _BATTLELIST_EXTRACTOR_CFG['click_x_offset'] = int(click_x_offset)


# PERF: [0.05485419999999941, 4.39999999990448e-06]
def getContent(screenshot: GrayImage, diag: dict | None = None) -> Union[GrayImage, None]:
    battleListIconPosition = getBattleListIconPosition(screenshot)
    if battleListIconPosition is None:
        if isinstance(diag, dict):
            diag['icon_pos'] = None
        return None

    want_images = False
    if isinstance(diag, dict):
        diag['icon_pos'] = tuple(int(v) for v in battleListIconPosition)
        want_images = bool(diag.get('want_images', False))

    # Infer capture scale from matched icon bbox vs template.
    try:
        tpl_h, tpl_w = images['icons']['ng_battleList'].shape[:2]
        _, _, found_w, found_h = battleListIconPosition
        sx = float(found_w) / float(tpl_w) if tpl_w else 1.0
        sy = float(found_h) / float(tpl_h) if tpl_h else 1.0
        scale = (sx + sy) / 2.0
        if scale <= 0:
            scale = 1.0
    except Exception:
        scale = 1.0

    if isinstance(diag, dict):
        diag['scale'] = float(scale)

    # Crop the battle list area in capture coordinates.
    list_left = int(battleListIconPosition[0] - 1)
    list_top = int(battleListIconPosition[1] + battleListIconPosition[3] + 1)
    list_width = int(max(40, round(156 * scale)))

    img_h, img_w = screenshot.shape[:2]
    if list_left < 0:
        list_left = 0
    if list_top < 0:
        list_top = 0
    if list_left >= img_w or list_top >= img_h:
        return None

    list_right = min(img_w, list_left + list_width)
    list_img = screenshot[list_top:img_h, list_left:list_right]
    if list_img.size == 0:
        return None

    if isinstance(diag, dict):
        diag['list_bbox'] = (int(list_left), int(list_top), int(list_right - list_left), int(img_h - list_top))
        diag['list_img_shape'] = getattr(list_img, 'shape', None)
        if want_images:
            diag['list_img'] = np.ascontiguousarray(list_img)

    # Find the bottom bar inside this cropped list.
    bottom_bar = locateMultiScale(
        list_img,
        images['containers']['bottomBar'],
        confidence=0.72,
        scales=(
            max(0.45, scale - 0.20),
            max(0.45, scale - 0.10),
            scale,
            scale + 0.10,
            scale + 0.20,
        ),
    )
    bottom_bar_source = 'multiscale' if bottom_bar is not None else None
    if bottom_bar is None:
        # Fallback: use legacy locator logic (may work on some layouts).
        bottom_bar = getContainerBottomBarPosition(list_img)
        if bottom_bar is not None:
            bottom_bar_source = 'legacy'
    if bottom_bar is None:
        if isinstance(diag, dict):
            diag['bottom_bar'] = None
        return None

    if isinstance(diag, dict):
        diag['bottom_bar'] = tuple(int(v) for v in bottom_bar)
        diag['bottom_bar_source'] = bottom_bar_source

    header_h = int(max(0, round(11 * scale)))
    content = list_img[: max(0, int(bottom_bar[1]) - header_h), :]
    if content.size == 0:
        return None

    if isinstance(diag, dict):
        diag['header_h_scaled'] = int(header_h)
        diag['content_pre_norm_shape'] = getattr(content, 'shape', None)
        if want_images:
            diag['content_pre_norm'] = np.ascontiguousarray(content)

    # Normalize back to canonical scale so the Numba-based parsing (22px rows, hashes)
    # keeps working regardless of OBS/DPI scaling.
    try:
        inv = 1.0 / float(scale) if scale > 0 else 1.0
        target_w = 156
        target_h = max(1, int(round(content.shape[0] * inv)))
        if content.shape[1] != target_w:
            # content.shape[1] should be ~156*scale; force it to 156.
            target_h = max(1, int(round(content.shape[0] * (float(target_w) / float(content.shape[1])))))
        interp = cv2.INTER_AREA if (content.shape[0] > target_h or content.shape[1] > target_w) else cv2.INTER_LINEAR
        content = cv2.resize(content, (target_w, target_h), interpolation=interp)
    except Exception:
        pass

    if isinstance(diag, dict):
        diag['content_shape'] = getattr(content, 'shape', None)

    return content

def getCreatureClickCoordinate(screenshot: GrayImage, *, index: int = 0) -> Union[XYCoordinate, None]:
    """Return a capture-local coordinate to click the given battle list row.

    This is used as a fallback when on-screen creature clicking is not available.
    """

    if screenshot is None or index < 0:
        return None

    # Preferred path: compute click position by mapping from the normalized (canonical)
    # content back to the pre-normalized crop. This is more robust than relying on
    # hard-coded scaled row heights, which can drift over multiple rows.
    try:
        diag: dict = {}
        content = getContent(screenshot, diag=diag)
        if content is not None and isinstance(diag.get('list_bbox'), tuple) and isinstance(diag.get('content_pre_norm_shape'), tuple):
            list_left, list_top, _, _ = diag['list_bbox']
            pre_h, pre_w = diag['content_pre_norm_shape'][:2]
            norm_h, norm_w = content.shape[:2]

            # Canonical layout used by parsing.
            header_norm = 11
            row_h_norm = 22

            # Click somewhere inside the name area (avoid the scrollbar on the right).
            x_offset_norm = int(_BATTLELIST_EXTRACTOR_CFG.get('click_x_offset', 60))
            x_norm = x_offset_norm
            y_norm = header_norm + (index * row_h_norm) + (row_h_norm // 2)

            # If the requested row isn't visible in the normalized content, don't click.
            if y_norm < 0 or y_norm >= norm_h:
                return None

            # Map normalized coords -> pre-normalized crop coords.
            sx = float(pre_w) / float(norm_w) if norm_w else 1.0
            sy = float(pre_h) / float(norm_h) if norm_h else 1.0
            x_pre = int(round(x_norm * sx))
            y_pre = int(round(y_norm * sy))

            click_x = int(list_left + x_pre)
            click_y = int(list_top + y_pre)

            if click_x < 0 or click_y < 0:
                return None
            if click_x >= screenshot.shape[1] or click_y >= screenshot.shape[0]:
                return None
            return (click_x, click_y)
    except Exception:
        pass

    # Fallback: legacy direct scaled math.
    battleListIconPosition = getBattleListIconPosition(screenshot)
    if battleListIconPosition is None:
        return None

    try:
        tpl_h, tpl_w = images['icons']['ng_battleList'].shape[:2]
        _, _, found_w, found_h = battleListIconPosition
        sx = float(found_w) / float(tpl_w) if tpl_w else 1.0
        sy = float(found_h) / float(tpl_h) if tpl_h else 1.0
        scale = (sx + sy) / 2.0
        if scale <= 0:
            scale = 1.0
    except Exception:
        scale = 1.0

    list_left = battleListIconPosition[0] - 1
    list_top = battleListIconPosition[1] + battleListIconPosition[3] + 1
    row_height = int(max(8, round(22 * scale)))
    header_height = int(max(0, round(11 * scale)))

    x_offset = int(_BATTLELIST_EXTRACTOR_CFG.get('click_x_offset', 60))
    click_x = int(list_left + int(round(x_offset * scale)))
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
