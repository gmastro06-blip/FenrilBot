import math
import os
from numba import njit
import numpy as np
from typing import Any, Dict, Optional, Union
import cv2
from src.shared.typings import Coordinate, GrayImage, GrayPixel, WaypointList
from src.utils.core import hashit, locate, locateMultiScale
from src.utils.coordinate import getCoordinateFromPixel, getPixelFromCoordinate
from .config import availableTilesFrictions, breakpointTileMovementSpeed, coordinates, dimensions, floorsImgs, floorsLevelsImgsHashes, floorsPathsSqms, images, nonWalkablePixelsColors, tilesFrictionsWithBreakpoints, walkableFloorsSqms
from .extractors import getRadarImage
from .locators import getRadarToolsPosition
from .typings import FloorLevel, TileFriction


# Cache a per-floor scale hint for minimap matching (helps with Tibia minimap zoom changes).
_radar_match_scale_hint: Dict[int, float] = {}


def _phase_correlate_shift(prev_img: np.ndarray, curr_img: np.ndarray) -> tuple[float, float, float]:
    """Estimate shift between two radar crops.

    Returns (dx, dy, response) where (dx, dy) is the translation of curr relative to prev
    (per OpenCV phaseCorrelate convention) and response is correlation strength.
    """
    try:
        ph, pw = prev_img.shape[:2]
        ch, cw = curr_img.shape[:2]
        h = int(min(ph, ch))
        w = int(min(pw, cw))
        if h <= 8 or w <= 8:
            return 0.0, 0.0, 0.0

        a = prev_img[:h, :w].astype(np.float32)
        b = curr_img[:h, :w].astype(np.float32)

        # Reduce low-frequency brightness/banding effects.
        a = a - cv2.GaussianBlur(a, (0, 0), 2.0)
        b = b - cv2.GaussianBlur(b, (0, 0), 2.0)

        win = cv2.createHanningWindow((w, h), cv2.CV_32F)
        (dx, dy), resp = cv2.phaseCorrelate(a, b, win)
        return float(dx), float(dy), float(resp)
    except Exception:
        return 0.0, 0.0, 0.0


def _scales_for_floor(floor_level: int) -> tuple[float, ...]:
    hint = _radar_match_scale_hint.get(int(floor_level))
    if hint is not None and hint > 0:
        # Try the hint first, then a small neighborhood.
        base = float(hint)
        neigh = (max(0.45, base - 0.10), max(0.45, base - 0.05), base, base + 0.05, base + 0.10)
        # De-duplicate while keeping order.
        out: list[float] = []
        for s in neigh:
            s = float(round(s, 3))
            if s not in out and 0.4 <= s <= 1.6:
                out.append(s)
        return tuple(out)
    # Default: include smaller scales (minimap zoomed-out) and near-1.0.
    return (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10)


# TODO: add unit tests
# TODO: add perf
# TODO: get by cached images coordinates hashes
def getCoordinate(
    screenshot: GrayImage,
    previousCoordinate: Optional[Coordinate] = None,
    debug: Optional[Dict[str, Any]] = None,
    previousRadarImage: Optional[GrayImage] = None,
) -> Optional[Coordinate]:
    radarToolsPosition = getRadarToolsPosition(screenshot)
    if radarToolsPosition is None:
        if debug is not None:
            debug['radar_tools'] = False
        return None
    radarImage = getRadarImage(screenshot, radarToolsPosition)
    if radarImage is None or getattr(radarImage, 'size', 0) == 0:
        if debug is not None:
            debug['radar_tools'] = True
            debug['floor_level'] = None
        return None

    # Hash-based fast path only works when the minimap crop matches the canonical size
    # used to build the hash database.
    try:
        rh, rw = radarImage.shape[:2]
    except Exception:
        rh, rw = 0, 0

    if rw == int(dimensions['width']) and rh == int(dimensions['height']):
        radarHashedImg: int = int(hashit(radarImage))
        hashedCoordinate = coordinates.get(radarHashedImg)
        if hashedCoordinate is not None:
            if debug is not None:
                debug['radar_tools'] = True
            return hashedCoordinate
    floorLevel = getFloorLevel(screenshot)
    if floorLevel is None:
        if debug is not None:
            debug['radar_tools'] = True
            debug['floor_level'] = None
        return None

    # Optional: seed the coordinate from an env var to disambiguate initial matching.
    # Format: "x,y,z" (z must match the detected floorLevel).
    if previousCoordinate is None:
        seed = os.environ.get('FENRIL_RADAR_SEED_COORD', '').strip()
        if seed:
            try:
                parts = [p.strip() for p in seed.replace(';', ',').split(',') if p.strip()]
                if len(parts) >= 3:
                    sx, sy, sz = int(parts[0]), int(parts[1]), int(parts[2])
                    if int(sz) == int(floorLevel):
                        previousCoordinate = (sx, sy, int(sz))
            except Exception:
                pass
    # Mask the player marker / center overlay so matching is less brittle.
    try:
        cy = int(rh // 2)
        cx = int(rw // 2)
        y0 = max(0, cy - 4)
        y1 = min(rh, cy + 4)
        x0 = max(0, cx - 4)
        x1 = min(rw, cx + 4)
        radarImage[y0:y1, x0:x1] = 128
    except Exception:
        pass
    if previousCoordinate is not None:
        (previousCoordinateXPixel, previousCoordinateYPixel) = getPixelFromCoordinate(
            previousCoordinate)

        # If we have the previous minimap crop, use phase-correlation tracking to get
        # a strong prior even when template matching is ambiguous (minimap zoom/theme).
        if previousRadarImage is not None and getattr(previousRadarImage, 'size', 0) != 0:
            dx, dy, resp = _phase_correlate_shift(previousRadarImage, radarImage)
            if debug is not None:
                debug['radar_phase_resp'] = resp
                debug['radar_phase_shift'] = (dx, dy)
            # Guardrails: ignore crazy jumps.
            if resp >= 0.15 and abs(dx) <= 25 and abs(dy) <= 25:
                # phaseCorrelate returns the shift of curr relative to prev content.
                # Player movement in floor pixels is the opposite direction.
                pred_xpx = int(previousCoordinateXPixel - round(dx))
                pred_ypx = int(previousCoordinateYPixel - round(dy))
                try:
                    (pred_x, pred_y) = getCoordinateFromPixel((pred_xpx, pred_ypx))
                    previousCoordinate = (pred_x, pred_y, previousCoordinate[2])
                    (previousCoordinateXPixel, previousCoordinateYPixel) = (pred_xpx, pred_ypx)
                except Exception:
                    pass
        paddingSize = 5
        half_h = int(rh // 2)
        half_w = int(rw // 2)
        yStart = previousCoordinateYPixel - (half_h + paddingSize)
        yEnd = previousCoordinateYPixel + (half_h + 1 + paddingSize)
        xStart = previousCoordinateXPixel - (half_w + paddingSize)
        xEnd = previousCoordinateXPixel + (half_w + paddingSize)
        areaImgToCompare = floorsImgs[floorLevel][yStart:yEnd, xStart:xEnd]
        # Local tracking: scores can be low under minimap zoom/theme, so use a lower
        # threshold in the constrained window and rely on temporal continuity.
        areaFoundImg = locate(areaImgToCompare, radarImage, confidence=0.35)
        if areaFoundImg is None:
            # Fallback: multiscale match for minimap zoom differences.
            scales = _scales_for_floor(int(floorLevel))
            areaFoundImg = locateMultiScale(areaImgToCompare, radarImage, confidence=0.35, scales=scales)
        if areaFoundImg:
            currentCoordinateXPixel = previousCoordinateXPixel - paddingSize + areaFoundImg[0]
            currentCoordinateYPixel = previousCoordinateYPixel - paddingSize + areaFoundImg[1]
            (currentCoordinateX, currentCoordinateY) = getCoordinateFromPixel(
                (currentCoordinateXPixel, currentCoordinateYPixel))
            try:
                # Update scale hint when multiscale returned a scaled bbox.
                aw = int(areaFoundImg[2])
                ah = int(areaFoundImg[3])
                if rw and rh:
                    _radar_match_scale_hint[int(floorLevel)] = float(((aw / rw) + (ah / rh)) / 2.0)
            except Exception:
                pass
            return (currentCoordinateX, currentCoordinateY, floorLevel)
    imgCoordinate = locate(floorsImgs[floorLevel], radarImage, confidence=0.75)
    if imgCoordinate is None:
        # Full-floor multiscale match (expensive): only used when single-scale fails.
        scales = _scales_for_floor(int(floorLevel))
        imgCoordinate = locateMultiScale(floorsImgs[floorLevel], radarImage, confidence=0.48, scales=scales)
    if imgCoordinate is None:
        return None
    xImgCoordinate = imgCoordinate[0] + int(imgCoordinate[2] // 2)
    yImgCoordinate = imgCoordinate[1] + int(imgCoordinate[3] // 2)
    try:
        if rw and rh:
            _radar_match_scale_hint[int(floorLevel)] = float(((int(imgCoordinate[2]) / rw) + (int(imgCoordinate[3]) / rh)) / 2.0)
    except Exception:
        pass
    xCoordinate, yCoordinate = getCoordinateFromPixel(
        (xImgCoordinate, yImgCoordinate))
    return (xCoordinate, yCoordinate, floorLevel)


# TODO: add unit tests
# TODO: add perf
def getFloorLevel(screenshot: GrayImage) -> Optional[FloorLevel]:
    radarToolsPosition = getRadarToolsPosition(screenshot)
    if radarToolsPosition is None:
        return None
    left, top, found_w, found_h = radarToolsPosition

    # Infer scale from the matched tools bbox relative to template size.
    try:
        tpl_h, tpl_w = images['tools'].shape[:2]
        scale_x = float(found_w) / float(tpl_w) if tpl_w else 1.0
        scale_y = float(found_h) / float(tpl_h) if tpl_h else 1.0
        scale = (scale_x + scale_y) / 2.0
        if scale <= 0:
            scale = 1.0
    except Exception:
        scale = 1.0

    # Original offsets/sizes (canonical): +8 px right of tools, -7 px up, 2x67 strip.
    x0 = int(left + found_w + int(round(8 * scale)))
    y0 = int(top - int(round(7 * scale)))
    w = max(1, int(round(2 * scale)))
    h = max(1, int(round(67 * scale)))
    x1 = x0 + w
    y1 = y0 + h

    img_h, img_w = screenshot.shape[:2]
    x0 = max(0, min(img_w, x0))
    x1 = max(0, min(img_w, x1))
    y0 = max(0, min(img_h, y0))
    y1 = max(0, min(img_h, y1))

    floorLevelImg = screenshot[y0:y1, x0:x1]
    if floorLevelImg.size == 0:
        return None

    # Normalize back to canonical size used by hashes.
    try:
        floorLevelImg = cv2.resize(floorLevelImg, (2, 67), interpolation=cv2.INTER_AREA if scale > 1.0 else cv2.INTER_LINEAR)
    except Exception:
        pass
    floorImgHash = hashit(floorLevelImg)
    if floorImgHash not in floorsLevelsImgsHashes:
        return None
    return floorsLevelsImgsHashes[floorImgHash]


# TODO: add unit tests
# TODO: add perf
def getClosestWaypointIndexFromCoordinate(coordinate: Coordinate, waypoints: WaypointList) -> Union[int, None]:
    closestWaypointIndex = None
    closestWaypointDistance: float = 9999.0
    for waypointIndex, waypoint in enumerate(waypoints):
        if waypoint['coordinate'][2] != coordinate[2]:
            continue
        dx = float(waypoint['coordinate'][0]) - float(coordinate[0])
        dy = float(waypoint['coordinate'][1]) - float(coordinate[1])
        waypointDistance = math.hypot(dx, dy)
        if waypointDistance < closestWaypointDistance:
            closestWaypointIndex = waypointIndex
            closestWaypointDistance = waypointDistance
    return closestWaypointIndex


# TODO: add perf
def getBreakpointTileMovementSpeed(charSpeed: int, tileFriction: TileFriction) -> int:
    tileFrictionNotFound = tileFriction not in tilesFrictionsWithBreakpoints
    if tileFrictionNotFound:
        closestTilesFrictions = np.flatnonzero(
            availableTilesFrictions > tileFriction)
        tileFriction = availableTilesFrictions[closestTilesFrictions[0]] if len(
            closestTilesFrictions) > 0 else 250
    availableBreakpointsIndexes = np.flatnonzero(
        charSpeed >= tilesFrictionsWithBreakpoints[tileFriction])
    if len(availableBreakpointsIndexes) == 0:
        return breakpointTileMovementSpeed[1]
    speed_key = int(availableBreakpointsIndexes[-1] + 1)
    if speed_key in breakpointTileMovementSpeed:
        return int(breakpointTileMovementSpeed[speed_key])
    return int(breakpointTileMovementSpeed[1])


# TODO: add unit tests
# TODO: add perf
def getTileFrictionByCoordinate(coordinate: Coordinate) -> TileFriction:
    xOfPixelCoordinate, yOfPixelCoordinate = getPixelFromCoordinate(
        coordinate)
    floorLevel = coordinate[2]
    tileFriction = floorsPathsSqms[floorLevel,
                                   yOfPixelCoordinate, xOfPixelCoordinate]
    return tileFriction


# TODO: add unit tests
# TODO: add perf
def isCloseToCoordinate(currentCoordinate: Coordinate, possibleCloseCoordinate: Coordinate, distanceTolerance: int = 10) -> bool:
    dx = float(possibleCloseCoordinate[0]) - float(currentCoordinate[0])
    dy = float(possibleCloseCoordinate[1]) - float(currentCoordinate[1])
    return math.hypot(dx, dy) <= distanceTolerance


# TODO: add unit tests
# TODO: add perf
# TODO: 2 coordinates was tested. Is very hard too test all coordinates(16 floors * 2560 mapWidth * 2048 mapHeight = 83.886.080 pixels)
# NumbaWarning: Cannot cache compiled function "isCoordinateWalkable" as it uses dynamic globals (such as ctypes pointers and large global arrays)
def isCoordinateWalkable(coordinate: Coordinate) -> bool:
    (xOfPixel, yOfPixel) = getPixelFromCoordinate(coordinate)
    return (walkableFloorsSqms[coordinate[2], yOfPixel, xOfPixel]) == 1


# TODO: add unit tests
# TODO: add perf
def isNonWalkablePixelColor(pixelColor: GrayPixel) -> bool:
    return bool(np.isin(pixelColor, nonWalkablePixelsColors))
