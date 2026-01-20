import cv2
import dxcam
import numpy as np
import hashlib
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, cast
from src.shared.typings import BBox, GrayImage


def _get_windows_monitors() -> Optional[List[Tuple[int, int, int, int]]]:
    """Return monitor rectangles in virtual-desktop coordinates."""
    try:
        import win32api

        monitors: List[Tuple[int, int, int, int]] = []
        for hmon, _, _ in win32api.EnumDisplayMonitors():
            info = win32api.GetMonitorInfo(hmon)
            rect = info.get('Monitor')
            if rect is not None:
                monitors.append((int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])))
        return monitors
    except Exception:
        return None


def getOutputIdxForPoint(x: int, y: int) -> Optional[int]:
    monitors = _get_windows_monitors()
    if not monitors:
        return None
    for idx, (l, t, r, b) in enumerate(monitors):
        if l <= x < r and t <= y < b:
            return idx
    return None


def getMonitorRectForPoint(x: int, y: int) -> Optional[Tuple[int, int, int, int]]:
    monitors = _get_windows_monitors()
    if not monitors:
        return None
    for (l, t, r, b) in monitors:
        if l <= x < r and t <= y < b:
            return (l, t, r, b)
    return None


try:
    from farmhash import FarmHash64

    def _hash_bytes(data: bytes) -> int:
        return FarmHash64(data)
except Exception:

    def _hash_bytes(data: bytes) -> int:
        return int.from_bytes(
            hashlib.blake2b(data, digest_size=8).digest(),
            "little",
            signed=False,
        )


_camera_cache: Dict[int, dxcam.DXCamera] = {}


def _create_camera(output_idx: int) -> dxcam.DXCamera:
    """Create (or reuse) a DXCamera for a given output.

    dxcam internally caches instances and prints a message when create() is called
    multiple times for the same device/output. We keep our own cache + idempotent
    output switching to avoid that spam.
    """
    idx = int(output_idx)
    cached = _camera_cache.get(idx)
    if cached is not None:
        return cached
    cam = dxcam.create(device_idx=0, output_idx=idx, output_color='BGRA')
    _camera_cache[idx] = cam
    return cam


def _recreate_camera(output_idx: int) -> dxcam.DXCamera:
    """Force-recreate a DXCamera instance for an output.

    We normally cache to avoid dxcam's stdout spam, but when dxcam starts
    returning black frames we need a real reset. This releases the cached
    instance (best-effort) and creates a fresh one.
    """
    idx = int(output_idx)
    old = _camera_cache.get(idx)
    if old is not None:
        try:
            # stop() is safe even if not started; release() frees resources.
            old.stop()
        except Exception:
            pass
        try:
            old.release()
        except Exception:
            pass
        try:
            del _camera_cache[idx]
        except Exception:
            pass

    cam = dxcam.create(device_idx=0, output_idx=idx, output_color='BGRA')
    _camera_cache[idx] = cam
    return cam


_preferred_output_idx = int(os.getenv('FENRIL_OUTPUT_IDX', '1'))
camera = _create_camera(_preferred_output_idx)
_camera_output_idx = _preferred_output_idx
latestScreenshot = None
_last_grab_was_none: bool = False
_consecutive_none_frames: int = 0
_consecutive_black_frames: int = 0
_consecutive_same_frames: int = 0
_last_screenshot_stats: Optional[Dict[str, Any]] = None
_last_dxcam_recover_log_time: float = 0.0
_last_frame_fingerprint: Optional[int] = None


def getScreenshotDebugInfo() -> Dict[str, Any]:
    return {
        'output_idx': _camera_output_idx,
        'last_grab_was_none': _last_grab_was_none,
        'consecutive_none_frames': _consecutive_none_frames,
        'consecutive_black_frames': _consecutive_black_frames,
        'consecutive_same_frames': _consecutive_same_frames,
        'last_stats': _last_screenshot_stats,
    }


def _frame_fingerprint(frame: np.ndarray) -> int:
    """Compute a cheap, stable fingerprint for a frame.

    Used to detect frozen capture (identical frames for long periods), which can
    cause cavebot stalls (radar/waypoints stop updating).
    """
    # Subsample aggressively to keep cost low.
    sample = frame[::32, ::32]
    try:
        return _hash_bytes(np.ascontiguousarray(sample).tobytes())
    except Exception:
        return _hash_bytes(bytes(sample.shape))


def setScreenshotOutputIdx(output_idx: int) -> None:
    global camera, _camera_output_idx
    idx = int(output_idx)
    if idx == _camera_output_idx and camera is not None:
        return
    camera = _create_camera(idx)
    _camera_output_idx = idx


def _sanitize_region(
    region: Optional[Tuple[int, int, int, int]],
    *,
    clamp_non_negative: bool,
) -> Optional[Tuple[int, int, int, int]]:
    if region is None:
        return None
    left, top, right, bottom = region
    left_i = int(left)
    top_i = int(top)
    right_i = int(right)
    bottom_i = int(bottom)
    if clamp_non_negative:
        left_i = max(0, left_i)
        top_i = max(0, top_i)
    if right_i <= left_i or bottom_i <= top_i:
        return None
    return (left_i, top_i, right_i, bottom_i)


def _grab_mss(absolute_region: Tuple[int, int, int, int]) -> Optional[GrayImage]:
    """Grab a grayscale frame using MSS.

    absolute_region is (left, top, right, bottom) in virtual-desktop coordinates.
    Returns a uint8 grayscale image or None.
    """
    try:
        from mss import mss
    except Exception:
        return None

    left, top, right, bottom = absolute_region
    width = int(right - left)
    height = int(bottom - top)
    if width <= 0 or height <= 0:
        return None

    try:
        with mss() as sct:
            mon = {'left': int(left), 'top': int(top), 'width': int(width), 'height': int(height)}
            img = np.array(sct.grab(mon))  # BGRA
        return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
    except Exception:
        return None


# TODO: add unit tests
def cacheObjectPosition(func: Callable[[GrayImage], Optional[BBox]]) -> Callable[[GrayImage], Optional[BBox]]:
    lastX = None
    lastY = None
    lastW = None
    lastH = None
    lastImgHash = None

    def reset_cache() -> None:
        nonlocal lastX, lastY, lastW, lastH, lastImgHash
        lastX = None
        lastY = None
        lastW = None
        lastH = None
        lastImgHash = None

    def inner(screenshot: GrayImage) -> Optional[BBox]:
        nonlocal lastX, lastY, lastW, lastH, lastImgHash
        if lastX is not None and lastY is not None and lastW is not None and lastH is not None:
            x = cast(int, lastX)
            y = cast(int, lastY)
            w = cast(int, lastW)
            h = cast(int, lastH)
            if hashit(screenshot[y:y + h, x:x + w]) == lastImgHash:
                return (x, y, w, h)
        res = func(screenshot)
        if res is None:
            return None
        lastX = res[0]
        lastY = res[1]
        lastW = res[2]
        lastH = res[3]
        lastImgHash = hashit(
            screenshot[lastY:lastY + lastH, lastX:lastX + lastW])
        return res
    # Attach a reset hook for recovery code (e.g., when radar tools can't be found).
    try:
        setattr(inner, 'reset_cache', reset_cache)
    except Exception:
        pass
    return inner


# TODO: add unit tests
def hashit(arr: np.ndarray) -> int:
    data = np.ascontiguousarray(arr).tobytes()
    return _hash_bytes(data)


# TODO: add unit tests
def locate(compareImage: GrayImage, img: GrayImage, confidence: float = 0.85, type: int = cv2.TM_CCOEFF_NORMED) -> Optional[BBox]:
    match = cv2.matchTemplate(compareImage, img, type)
    res = cv2.minMaxLoc(match)
    if res[1] <= confidence:
        return None
    return res[3][0], res[3][1], len(img[0]), len(img)


def locateMultiScale(
    compareImage: GrayImage,
    img: GrayImage,
    confidence: float = 0.85,
    scales: Optional[Sequence[float]] = None,
    type: int = cv2.TM_CCOEFF_NORMED,
) -> Optional[BBox]:
    """Template matching across multiple scales.

    Useful when capture output is scaled (e.g., OBS projector, DPI scaling).
    Returns the best match bbox in compareImage coordinates.
    """
    if scales is None:
        scales = (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15)

    best_val: float = -1.0
    best_loc: Optional[Tuple[int, int]] = None
    best_w: int = 0
    best_h: int = 0

    try:
        base_h, base_w = img.shape[:2]
        cmp_h, cmp_w = compareImage.shape[:2]
    except Exception:
        return None

    for s in scales:
        try:
            if s <= 0:
                continue
            w = max(1, int(round(base_w * float(s))))
            h = max(1, int(round(base_h * float(s))))
            if w > cmp_w or h > cmp_h:
                continue
            interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR
            templ = cv2.resize(img, (w, h), interpolation=interp)
            match = cv2.matchTemplate(compareImage, templ, type)
            _, max_val, _, max_loc = cv2.minMaxLoc(match)
            if max_val > best_val:
                best_val = float(max_val)
                best_loc = (int(max_loc[0]), int(max_loc[1]))
                best_w = int(w)
                best_h = int(h)
        except Exception:
            continue

    if best_loc is None or best_val <= confidence:
        return None
    return best_loc[0], best_loc[1], best_w, best_h


# TODO: add unit tests
def locateMultiple(compareImg: GrayImage, img: GrayImage, confidence: float = 0.85) -> List[BBox]:
    match = cv2.matchTemplate(compareImg, img, cv2.TM_CCOEFF_NORMED)
    loc = np.where(match >= confidence)
    resultList = []
    for pt in zip(*loc[::-1]):
        resultList.append((pt[0], pt[1], len(compareImg[0]), len(compareImg)))
    return resultList


# TODO: add unit tests
def getScreenshot(
    region: Optional[Tuple[int, int, int, int]] = None,
    absolute_region: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[GrayImage]:
    global camera, latestScreenshot, _camera_output_idx
    global _last_grab_was_none, _consecutive_none_frames, _consecutive_black_frames, _consecutive_same_frames, _last_screenshot_stats
    global _last_frame_fingerprint
    global _last_dxcam_recover_log_time
    # dxcam region is relative to a specific output (top-left is always (0,0))
    region = _sanitize_region(region, clamp_non_negative=True)
    # absolute_region is in virtual-desktop coordinates and may be negative
    # (e.g. when a secondary monitor is placed left/up of the primary).
    abs_region = _sanitize_region(absolute_region, clamp_non_negative=False)
    try:
        screenshot = camera.grab(region=region) if region is not None else camera.grab()
    except Exception:
        screenshot = None

    _last_grab_was_none = screenshot is None
    if screenshot is None:
        _consecutive_none_frames += 1
    else:
        _consecutive_none_frames = 0

    # Fallback for single-monitor setups where output_idx=1 doesn't exist/doesn't capture.
    if screenshot is None and _camera_output_idx != 0:
        try:
            setScreenshotOutputIdx(0)
            screenshot = camera.grab(region=region) if region is not None else camera.grab()
        except Exception:
            screenshot = None

        _last_grab_was_none = screenshot is None
        if screenshot is None:
            _consecutive_none_frames += 1
        else:
            _consecutive_none_frames = 0

    # Optional MSS fallback when dxcam returns None.
    # NOTE: MSS/GDI capture often returns black for GPU-accelerated windows (e.g. OBS/projectors).
    mss_fallback_on_none = os.getenv('FENRIL_MSS_FALLBACK_ON_NONE', '0') != '0'
    if screenshot is None and mss_fallback_on_none and abs_region is not None:
        mss_frame = _grab_mss(abs_region)
        if mss_frame is not None:
            latestScreenshot = mss_frame
            _last_grab_was_none = False
            _consecutive_none_frames = 0
            # update stats
            try:
                mean_val = float(np.mean(mss_frame))
                std_val = float(np.std(mss_frame))
                _last_screenshot_stats = {
                    'shape': tuple(mss_frame.shape),
                    'mean': mean_val,
                    'std': std_val,
                    'region': region,
                    'absolute_region': abs_region,
                    'backend': 'mss',
                }
                _consecutive_black_frames = 0
            except Exception:
                _last_screenshot_stats = None
            return latestScreenshot

    if screenshot is None:
        return latestScreenshot
    latestScreenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)

    # Lightweight stats + black-frame heuristic (used by diagnostics).
    try:
        frame = cast(GrayImage, latestScreenshot)
        fp = _frame_fingerprint(cast(np.ndarray, frame))
        if _last_frame_fingerprint is not None and fp == _last_frame_fingerprint:
            _consecutive_same_frames += 1
        else:
            _consecutive_same_frames = 0
        _last_frame_fingerprint = fp

        mean_val = float(np.mean(frame))
        std_val = float(np.std(frame))
        dark_px_thr = int(os.getenv('FENRIL_BLACK_DARK_PIXEL_THRESHOLD', '8'))
        dark_frac_thr = float(os.getenv('FENRIL_BLACK_DARK_FRACTION_THRESHOLD', '0.98'))
        dark_fraction = float(np.mean(frame <= dark_px_thr))
        _last_screenshot_stats = {
            'shape': tuple(frame.shape),
            'mean': mean_val,
            'std': std_val,
            'dark_fraction': dark_fraction,
            'fingerprint': fp,
            'region': region,
            'absolute_region': abs_region,
            'backend': 'dxcam',
        }
        std_thr = float(os.getenv('FENRIL_BLACK_STD_THRESHOLD', '2.0'))
        mean_thr = float(os.getenv('FENRIL_BLACK_MEAN_THRESHOLD', '10.0'))
        mean_force_thr = float(os.getenv('FENRIL_BLACK_MEAN_FORCE_THRESHOLD', '3.0'))
        # Some setups return "mostly black" frames with random noise; std can be high.
        # Treat as black if it's dark on average and most pixels are near-black.
        is_probably_black = (mean_val < mean_thr) and (
            mean_val <= mean_force_thr or std_val < std_thr or dark_fraction >= dark_frac_thr
        )

        # If the frame is *completely* black, try an immediate dxcam retry/recover.
        # This is a common transient dxcam glitch and retrying avoids stalling the pipeline.
        hard_black = mean_val <= 0.5 and std_val <= 0.5
        if hard_black and os.getenv('FENRIL_DXCAM_RETRY_ON_HARD_BLACK', '1') != '0':
            try:
                # Re-grab once without recreating the camera.
                # Calling dxcam.create repeatedly can spam stdout.
                shot2 = camera.grab(region=region) if region is not None else camera.grab()
                if shot2 is not None:
                    frame2 = cv2.cvtColor(shot2, cv2.COLOR_BGRA2GRAY)
                    mean2 = float(np.mean(frame2))
                    std2 = float(np.std(frame2))
                    if not (mean2 <= 0.5 and std2 <= 0.5):
                        latestScreenshot = cast(GrayImage, frame2)
                        frame = cast(GrayImage, latestScreenshot)
                        mean_val = mean2
                        std_val = std2
                        dark_fraction = float(np.mean(frame <= dark_px_thr))
                        _last_screenshot_stats = {
                            'shape': tuple(frame.shape),
                            'mean': mean_val,
                            'std': std_val,
                            'dark_fraction': dark_fraction,
                            'region': region,
                            'absolute_region': abs_region,
                            'backend': 'dxcam',
                            'retried_hard_black': True,
                        }
                        is_probably_black = (mean_val < mean_thr) and (
                            mean_val <= mean_force_thr or std_val < std_thr or dark_fraction >= dark_frac_thr
                        )
            except Exception:
                pass
        if is_probably_black:
            _consecutive_black_frames += 1
        else:
            _consecutive_black_frames = 0
    except Exception:
        _last_screenshot_stats = None

    black_threshold = int(os.getenv('FENRIL_BLACK_FRAME_THRESHOLD', '8'))

    # Detect frozen capture (same frame for a long time) and try to recover.
    stale_threshold = int(os.getenv('FENRIL_SAME_FRAME_THRESHOLD', '300'))
    recover_on_stale = os.getenv('FENRIL_DXCAM_RECOVER_ON_STALE', '1') != '0'
    if recover_on_stale and _consecutive_same_frames >= stale_threshold:
        try:
            camera = _recreate_camera(_camera_output_idx)
            shot2 = camera.grab(region=region) if region is not None else camera.grab()
        except Exception:
            shot2 = None
        if shot2 is not None:
            try:
                frame2 = cv2.cvtColor(shot2, cv2.COLOR_BGRA2GRAY)
                latestScreenshot = cast(GrayImage, frame2)
                _consecutive_same_frames = 0
                _last_frame_fingerprint = _frame_fingerprint(cast(np.ndarray, frame2))

                if os.getenv('FENRIL_LOG_DXCAM_RECOVERY', '1') != '0':
                    now = time.time()
                    if now - _last_dxcam_recover_log_time >= 5.0:
                        _last_dxcam_recover_log_time = now
                        try:
                            print(
                                f"[fenril][dxcam] Recovered from stale frames (output_idx={_camera_output_idx} region={region})"
                            )
                        except Exception:
                            pass
                return latestScreenshot
            except Exception:
                pass

    # Prefer recovering dxcam (recreate the camera) over MSS fallback.
    dxcam_recover = os.getenv('FENRIL_DXCAM_RECOVER_ON_BLACK', '1') != '0'
    if dxcam_recover and _consecutive_black_frames >= black_threshold:
        try:
            camera = _recreate_camera(_camera_output_idx)
            shot2 = camera.grab(region=region) if region is not None else camera.grab()
        except Exception:
            shot2 = None
        if shot2 is not None:
            try:
                frame2 = cv2.cvtColor(shot2, cv2.COLOR_BGRA2GRAY)
                mean2 = float(np.mean(frame2))
                std2 = float(np.std(frame2))
                dark_px_thr = int(os.getenv('FENRIL_BLACK_DARK_PIXEL_THRESHOLD', '8'))
                dark_frac_thr = float(os.getenv('FENRIL_BLACK_DARK_FRACTION_THRESHOLD', '0.98'))
                dark_fraction2 = float(np.mean(frame2 <= dark_px_thr))
                std_thr = float(os.getenv('FENRIL_BLACK_STD_THRESHOLD', '2.0'))
                mean_thr = float(os.getenv('FENRIL_BLACK_MEAN_THRESHOLD', '10.0'))
                mean_force_thr = float(os.getenv('FENRIL_BLACK_MEAN_FORCE_THRESHOLD', '3.0'))
                recovered_is_black = (mean2 < mean_thr) and (
                    mean2 <= mean_force_thr or std2 < std_thr or dark_fraction2 >= dark_frac_thr
                )
                if not recovered_is_black:
                    latestScreenshot = cast(GrayImage, frame2)
                    _consecutive_black_frames = 0
                    _last_screenshot_stats = {
                        'shape': tuple(frame2.shape),
                        'mean': mean2,
                        'std': std2,
                        'dark_fraction': dark_fraction2,
                        'region': region,
                        'absolute_region': abs_region,
                        'backend': 'dxcam',
                        'recovered_dxcam': True,
                    }

                    # Helpful runtime signal (throttled).
                    if os.getenv('FENRIL_LOG_DXCAM_RECOVERY', '1') != '0':
                        now = time.time()
                        if now - _last_dxcam_recover_log_time >= 5.0:
                            _last_dxcam_recover_log_time = now
                            try:
                                print(
                                    f"[fenril][dxcam] Recovered from black frames (output_idx={_camera_output_idx} region={region})"
                                )
                            except Exception:
                                pass
                    return latestScreenshot
            except Exception:
                pass

    # Optional MSS fallback when dxcam is producing black frames.
    # Disabled by default because it commonly returns black for OBS/projectors.
    mss_fallback = os.getenv('FENRIL_MSS_FALLBACK', '0') != '0'
    if mss_fallback and abs_region is not None and _consecutive_black_frames >= black_threshold:
        mss_frame = _grab_mss(abs_region)
        if mss_frame is not None:
            try:
                mean2 = float(np.mean(mss_frame))
                std2 = float(np.std(mss_frame))
                # If MSS also returns black, ignore it and keep the last good frame.
                if mean2 <= 0.5 and std2 <= 0.5:
                    return latestScreenshot
                latestScreenshot = mss_frame
                _consecutive_black_frames = 0
                _last_screenshot_stats = {
                    'shape': tuple(mss_frame.shape),
                    'mean': mean2,
                    'std': std2,
                    'region': region,
                    'absolute_region': abs_region,
                    'backend': 'mss',
                    'switched_due_to_black_frames': True,
                }
            except Exception:
                _last_screenshot_stats = None
            return latestScreenshot
    return latestScreenshot
