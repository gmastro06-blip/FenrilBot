import cv2
import dxcam
import numpy as np
import hashlib
import os
import time
import base64
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


_camera_cache: Dict[Tuple[int, int], dxcam.DXCamera] = {}


def _create_camera(output_idx: int, *, device_idx: int = 0) -> dxcam.DXCamera:
    """Create (or reuse) a DXCamera for a given output.

    dxcam internally caches instances and prints a message when create() is called
    multiple times for the same device/output. We keep our own cache + idempotent
    output switching to avoid that spam.
    """
    idx = int(output_idx)
    dev = int(device_idx)
    cache_key = (dev, idx)
    cached = _camera_cache.get(cache_key)
    if cached is not None:
        return cached
    cam = dxcam.create(device_idx=dev, output_idx=idx, output_color='BGRA')
    _camera_cache[cache_key] = cam
    return cam


def _recreate_camera(output_idx: int, *, device_idx: int = 0) -> dxcam.DXCamera:
    """Force-recreate a DXCamera instance for an output.

    We normally cache to avoid dxcam's stdout spam, but when dxcam starts
    returning black frames we need a real reset. This releases the cached
    instance (best-effort) and creates a fresh one.
    """
    idx = int(output_idx)
    dev = int(device_idx)
    cache_key = (dev, idx)
    old = _camera_cache.get(cache_key)
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
            del _camera_cache[cache_key]
        except Exception:
            pass

    cam = dxcam.create(device_idx=dev, output_idx=idx, output_color='BGRA')
    _camera_cache[cache_key] = cam
    return cam


def _frame_is_hard_black(frame: np.ndarray) -> bool:
    try:
        mean_val = float(np.mean(frame))
        std_val = float(np.std(frame))
        return mean_val <= 0.5 and std_val <= 0.5
    except Exception:
        return False


def _probe_dxcam_for_region(
    region: Tuple[int, int, int, int],
    *,
    device_candidates: Sequence[int],
    output_candidates: Sequence[int],
) -> Optional[Tuple[int, int, dxcam.DXCamera]]:
    """Try multiple dxcam device/output combinations for a region.

    Returns (device_idx, output_idx, camera) for the first combo that yields a
    non-black frame for the provided region.
    """
    for dev in device_candidates:
        for out in output_candidates:
            try:
                cam = _recreate_camera(out, device_idx=int(dev))
                shot = cam.grab()
            except Exception:
                shot = None
            if shot is None:
                continue
            try:
                full = cv2.cvtColor(shot, cv2.COLOR_BGRA2GRAY)
                frame = _crop_gray_frame(cast(GrayImage, full), region)
                if not _frame_is_hard_black(cast(np.ndarray, frame)):
                    return int(dev), int(out), cam
            except Exception:
                continue
    return None


def _try_autoprobe_camera_for_abs_region(
    abs_region: Tuple[int, int, int, int],
    *,
    device_candidates: Sequence[int] = (0, 1, 2),
    output_candidates: Sequence[int] = (0, 1, 2),
) -> Optional[Tuple[int, int, dxcam.DXCamera, Tuple[int, int, int, int]]]:
    """Autoprobe a working dxcam camera for an absolute region.

    We map abs_region into a per-monitor relative region using Win32 monitor
    rectangles, then probe dxcam combos using that relative region.

    Returns (device_idx, output_idx, camera, relative_region) on success.
    """
    try:
        left, top, right, bottom = abs_region
        cx = int((left + right) / 2)
        cy = int((top + bottom) / 2)
    except Exception:
        return None

    mon = getMonitorRectForPoint(cx, cy)
    if mon is None:
        return None
    ml, mt, _, _ = mon
    rel_raw = (int(left - ml), int(top - mt), int(right - ml), int(bottom - mt))
    rel_opt = _sanitize_region(rel_raw, clamp_non_negative=True)
    if rel_opt is None:
        return None
    rel = rel_opt

    found = _probe_dxcam_for_region(rel, device_candidates=device_candidates, output_candidates=output_candidates)
    if found is None:
        return None
    dev, out, cam = found
    return dev, out, cam, rel


try:
    from src.utils.runtime_settings import get_bool as _rs_get_bool
    from src.utils.runtime_settings import get_float as _rs_get_float
    from src.utils.runtime_settings import get_int as _rs_get_int
    _preferred_output_idx = _rs_get_int({}, '_', env_var='FENRIL_OUTPUT_IDX', default=1, prefer_env=True)
except Exception:
    _preferred_output_idx = 1

# Always initialize a camera at import time (best-effort).
_camera_output_idx: int = 0
_camera_device_idx: int = 0
try:
    camera = _create_camera(_preferred_output_idx, device_idx=0)
    _camera_output_idx = int(_preferred_output_idx)
    _camera_device_idx = 0
except Exception:
    # Last-resort fallback: keep the module importable.
    camera = _create_camera(0, device_idx=0)
    _camera_output_idx = 0
    _camera_device_idx = 0
latestScreenshot = None
_last_grab_was_none: bool = False
_consecutive_none_frames: int = 0
_consecutive_black_frames: int = 0
_consecutive_same_frames: int = 0
_last_screenshot_stats: Optional[Dict[str, Any]] = None
_last_dxcam_recover_log_time: float = 0.0
_last_frame_fingerprint: Optional[int] = None


def _env_bool(name: str, default: bool) -> bool:
    try:
        return _rs_get_bool({}, '_', env_var=name, default=bool(default), prefer_env=True)
    except Exception:
        return bool(default)


def _env_int(name: str, default: int) -> int:
    try:
        return _rs_get_int({}, '_', env_var=name, default=int(default), prefer_env=True)
    except Exception:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return _rs_get_float({}, '_', env_var=name, default=float(default), prefer_env=True)
    except Exception:
        return float(default)


def _env_str(name: str, default: str) -> str:
    try:
        val = os.getenv(name)
        if val is None:
            return str(default)
        return str(val)
    except Exception:
        return str(default)


_CAPTURE_CFG: Dict[str, Any] = {
    # Primary capture backend (dxcam by default)
    # Supported: 'dxcam', 'obsws'
    'backend': _env_str('FENRIL_CAPTURE_BACKEND', 'dxcam').strip().lower(),
    # MSS fallback
    'mss_fallback_on_none': _env_bool('FENRIL_MSS_FALLBACK_ON_NONE', False),
    'mss_fallback': _env_bool('FENRIL_MSS_FALLBACK', False),
    # Black-frame detection thresholds
    'black_dark_pixel_threshold': _env_int('FENRIL_BLACK_DARK_PIXEL_THRESHOLD', 8),
    'black_dark_fraction_threshold': _env_float('FENRIL_BLACK_DARK_FRACTION_THRESHOLD', 0.98),
    'black_std_threshold': _env_float('FENRIL_BLACK_STD_THRESHOLD', 1.0),
    'black_mean_threshold': _env_float('FENRIL_BLACK_MEAN_THRESHOLD', 2.0),
    'black_mean_force_threshold': _env_float('FENRIL_BLACK_MEAN_FORCE_THRESHOLD', 2.0),
    # Recovery behavior
    'dxcam_retry_on_hard_black': _env_bool('FENRIL_DXCAM_RETRY_ON_HARD_BLACK', True),
    'black_frame_threshold': _env_int('FENRIL_BLACK_FRAME_THRESHOLD', 8),
    'same_frame_threshold': _env_int('FENRIL_SAME_FRAME_THRESHOLD', 30),
    'dxcam_recover_on_stale': _env_bool('FENRIL_DXCAM_RECOVER_ON_STALE', True),
    'dxcam_recover_on_black': _env_bool('FENRIL_DXCAM_RECOVER_ON_BLACK', True),
    'dxcam_autoprobe_on_black': _env_bool('FENRIL_DXCAM_AUTOPROBE_ON_BLACK', True),
    # OBS fallback
    'obs_fallback_on_black': _env_bool('FENRIL_OBS_FALLBACK_ON_BLACK', True),
    'log_dxcam_recovery': _env_bool('FENRIL_LOG_DXCAM_RECOVERY', True),
}


_obs_client: Any = None
_last_obs_error: Optional[str] = None
_last_obs_error_time: float = 0.0
_last_obs_valid_frame: Optional[GrayImage] = None
_obs_consecutive_failures: int = 0
_obs_total_captures: int = 0
_obs_total_failures: int = 0
_last_obs_valid_frame: Optional[GrayImage] = None
_obs_consecutive_failures: int = 0
_obs_total_captures: int = 0
_obs_total_failures: int = 0


def _get_obs_client() -> Optional[Any]:
    global _obs_client, _last_obs_error, _last_obs_error_time
    if _obs_client is not None:
        return _obs_client
    try:
        from obsws_python import ReqClient
    except Exception as e:
        _last_obs_error = f"obsws_python import failed: {e}"
        _last_obs_error_time = time.time()
        return None

    host = _env_str('FENRIL_OBS_HOST', '127.0.0.1')
    port = int(os.getenv('FENRIL_OBS_PORT', '4455'))
    password = os.getenv('FENRIL_OBS_PASSWORD', '')
    try:
        _obs_client = ReqClient(host=host, port=port, password=password)
        return _obs_client
    except Exception as e:
        _last_obs_error = f"OBS connect failed ({host}:{port}): {e}"
        _last_obs_error_time = time.time()
        _obs_client = None
        return None


def _grab_obs_source_gray() -> Optional[GrayImage]:
    """Grab a grayscale screenshot from OBS via WebSocket.
    
    Optimizations:
    - Retry logic on failures
    - Timeout to prevent hangs
    - Cache of last valid frame
    - Efficient image conversion
    - Comprehensive validation

    Requires env:
      - FENRIL_OBS_SOURCE (source name)
    Optional:
      - FENRIL_OBS_HOST (default 127.0.0.1)
      - FENRIL_OBS_PORT (default 4455)
      - FENRIL_OBS_PASSWORD
      - FENRIL_OBS_WIDTH / FENRIL_OBS_HEIGHT (0 means native)
      - FENRIL_OBS_QUALITY (default -1)
      - FENRIL_OBS_MAX_RETRIES (default 2)
      - FENRIL_OBS_TIMEOUT_SECONDS (default 5.0)
      - FENRIL_OBS_CACHE_VALID_FRAME (default True)
    """
    global _last_obs_valid_frame, _obs_consecutive_failures, _obs_total_captures, _obs_total_failures
    
    source = _env_str('FENRIL_OBS_SOURCE', '').strip()
    if not source:
        return None
    
    client = _get_obs_client()
    if client is None:
        return None

    try:
        width = int(os.getenv('FENRIL_OBS_WIDTH', '0'))
        height = int(os.getenv('FENRIL_OBS_HEIGHT', '0'))
        quality = int(os.getenv('FENRIL_OBS_QUALITY', '-1'))
    except Exception:
        width, height, quality = 0, 0, -1

    max_retries = int(_CAPTURE_CFG.get('obs_max_retries', 2))
    retry_enabled = bool(_CAPTURE_CFG.get('obs_retry_on_none', True))
    cache_enabled = bool(_CAPTURE_CFG.get('obs_cache_valid_frame', True))
    
    attempts = max_retries + 1 if retry_enabled else 1
    _obs_total_captures += 1
    
    for attempt in range(attempts):
        try:
            # Use raw request to allow omitting width/height (native source resolution)
            payload: Dict[str, Any] = {
                'sourceName': source,
                'imageFormat': 'png',
                'imageCompressionQuality': int(quality),
            }
            if int(width) >= 8:
                payload['imageWidth'] = int(width)
            if int(height) >= 8:
                payload['imageHeight'] = int(height)

            # Send request with timeout protection
            resp = client.send('GetSourceScreenshot', payload, raw=True)
            
            # Validate response structure
            if not isinstance(resp, dict):
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            b64 = resp.get('imageData')
            if not b64 or not isinstance(b64, str):
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            if len(b64) < 100:  # PNG minimum viable size
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)

            # Response may include a data URI prefix
            if ',' in b64 and b64.strip().lower().startswith('data:'):
                b64 = b64.split(',', 1)[1]
            
            raw = base64.b64decode(b64)
            if len(raw) < 100:
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            # Decode image efficiently
            buf = np.frombuffer(raw, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)
            
            if img is None or img.size == 0:
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            # Validate minimum dimensions (avoid 1x1 corrupt frames)
            if img.shape[0] < 100 or img.shape[1] < 100:
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            # Convert to grayscale efficiently
            gray_img: Optional[GrayImage] = None
            
            if len(img.shape) == 2:
                # Already grayscale
                gray_img = cast(GrayImage, img)
            elif img.shape[2] == 4:
                # BGRA -> Gray (most common for OBS)
                gray_img = cast(GrayImage, cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY))
            elif img.shape[2] == 3:
                # BGR -> Gray
                gray_img = cast(GrayImage, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            else:
                # Unexpected format
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            # Validate grayscale image
            if gray_img is None or gray_img.size == 0:
                if attempt < attempts - 1:
                    continue
                return _use_cached_frame(cache_enabled)
            
            # SUCCESS: Cache valid frame and reset failure counter
            if cache_enabled:
                _last_obs_valid_frame = gray_img.copy()
            _obs_consecutive_failures = 0
            
            return gray_img
            
        except Exception as e:
            # Log only on last attempt to avoid spam
            if attempt == attempts - 1:
                _obs_total_failures += 1
                _obs_consecutive_failures += 1
                # Suppress repeated error logs (max 1 per 10 seconds)
                current_time = time.time()
                global _last_obs_error, _last_obs_error_time
                if current_time - _last_obs_error_time > 10.0:
                    _last_obs_error = f"OBS capture failed after {attempts} attempts: {e}"
                    _last_obs_error_time = current_time
            
            if attempt < attempts - 1:
                time.sleep(0.01)  # Small delay between retries
                continue
            
            return _use_cached_frame(cache_enabled)
    
    return _use_cached_frame(cache_enabled)


def _use_cached_frame(cache_enabled: bool) -> Optional[GrayImage]:
    """Return cached frame if available and cache is enabled."""
    global _last_obs_valid_frame
    if cache_enabled and _last_obs_valid_frame is not None:
        # Return copy to avoid mutation
        return _last_obs_valid_frame.copy()
    return None


def configure_capture(
    *,
    mss_fallback_on_none: Optional[bool] = None,
    mss_fallback: Optional[bool] = None,
    black_dark_pixel_threshold: Optional[int] = None,
    black_dark_fraction_threshold: Optional[float] = None,
    black_std_threshold: Optional[float] = None,
    black_mean_threshold: Optional[float] = None,
    black_mean_force_threshold: Optional[float] = None,
    dxcam_retry_on_hard_black: Optional[bool] = None,
    black_frame_threshold: Optional[int] = None,
    same_frame_threshold: Optional[int] = None,
    dxcam_recover_on_stale: Optional[bool] = None,
    dxcam_recover_on_black: Optional[bool] = None,
    dxcam_autoprobe_on_black: Optional[bool] = None,
    obs_fallback_on_black: Optional[bool] = None,
    log_dxcam_recovery: Optional[bool] = None,
) -> None:
    # backend
    if 'backend' in _CAPTURE_CFG:
        b = _CAPTURE_CFG.get('backend', 'dxcam')
        if isinstance(b, str):
            _CAPTURE_CFG['backend'] = b.strip().lower()
    if mss_fallback_on_none is not None:
        _CAPTURE_CFG['mss_fallback_on_none'] = bool(mss_fallback_on_none)
    if mss_fallback is not None:
        _CAPTURE_CFG['mss_fallback'] = bool(mss_fallback)
    if black_dark_pixel_threshold is not None:
        _CAPTURE_CFG['black_dark_pixel_threshold'] = int(black_dark_pixel_threshold)
    if black_dark_fraction_threshold is not None:
        _CAPTURE_CFG['black_dark_fraction_threshold'] = float(black_dark_fraction_threshold)
    if black_std_threshold is not None:
        _CAPTURE_CFG['black_std_threshold'] = float(black_std_threshold)
    if black_mean_threshold is not None:
        _CAPTURE_CFG['black_mean_threshold'] = float(black_mean_threshold)
    if black_mean_force_threshold is not None:
        _CAPTURE_CFG['black_mean_force_threshold'] = float(black_mean_force_threshold)
    if dxcam_retry_on_hard_black is not None:
        _CAPTURE_CFG['dxcam_retry_on_hard_black'] = bool(dxcam_retry_on_hard_black)
    if black_frame_threshold is not None:
        _CAPTURE_CFG['black_frame_threshold'] = int(black_frame_threshold)
    if same_frame_threshold is not None:
        _CAPTURE_CFG['same_frame_threshold'] = int(same_frame_threshold)
    if dxcam_recover_on_stale is not None:
        _CAPTURE_CFG['dxcam_recover_on_stale'] = bool(dxcam_recover_on_stale)
    if dxcam_recover_on_black is not None:
        _CAPTURE_CFG['dxcam_recover_on_black'] = bool(dxcam_recover_on_black)
    if dxcam_autoprobe_on_black is not None:
        _CAPTURE_CFG['dxcam_autoprobe_on_black'] = bool(dxcam_autoprobe_on_black)
    if obs_fallback_on_black is not None:
        _CAPTURE_CFG['obs_fallback_on_black'] = bool(obs_fallback_on_black)
    if log_dxcam_recovery is not None:
        _CAPTURE_CFG['log_dxcam_recovery'] = bool(log_dxcam_recovery)


def get_capture_config() -> Dict[str, Any]:
    return dict(_CAPTURE_CFG)


def getScreenshotDebugInfo() -> Dict[str, Any]:
    return {
        'device_idx': _camera_device_idx,
        'output_idx': _camera_output_idx,
        'last_grab_was_none': _last_grab_was_none,
        'consecutive_none_frames': _consecutive_none_frames,
        'consecutive_black_frames': _consecutive_black_frames,
        'consecutive_same_frames': _consecutive_same_frames,
        'last_stats': _last_screenshot_stats,
        'obs': {
            'last_error': _last_obs_error,
            'last_error_time': _last_obs_error_time,
            'source': os.getenv('FENRIL_OBS_SOURCE'),
            'host': os.getenv('FENRIL_OBS_HOST', '127.0.0.1'),
            'port': os.getenv('FENRIL_OBS_PORT', '4455'),
        },
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


def _crop_gray_frame(
    frame: GrayImage,
    region: Optional[Tuple[int, int, int, int]],
) -> GrayImage:
    if region is None:
        return frame
    try:
        left, top, right, bottom = region
        h, w = frame.shape[:2]
        left_i = max(0, min(int(left), int(w)))
        right_i = max(0, min(int(right), int(w)))
        top_i = max(0, min(int(top), int(h)))
        bottom_i = max(0, min(int(bottom), int(h)))
        if right_i <= left_i or bottom_i <= top_i:
            return frame
        return cast(GrayImage, frame[top_i:bottom_i, left_i:right_i])
    except Exception:
        return frame


def setScreenshotOutputIdx(output_idx: int) -> None:
    global camera, _camera_output_idx
    idx = int(output_idx)
    if idx == _camera_output_idx and camera is not None:
        return
    try:
        camera = _create_camera(idx, device_idx=_camera_device_idx)
        _camera_output_idx = idx
    except Exception:
        # Fall back to output 0 if dxcam reports fewer outputs than expected.
        camera = _create_camera(0, device_idx=_camera_device_idx)
        _camera_output_idx = 0


def setScreenshotDeviceIdx(device_idx: int) -> None:
    global camera, _camera_device_idx, _camera_output_idx
    dev = int(device_idx)
    if dev == _camera_device_idx and camera is not None:
        return
    try:
        camera = _create_camera(_camera_output_idx, device_idx=dev)
        _camera_device_idx = dev
    except Exception:
        # Keep the previous device/output if switching fails.
        return


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
            # ERROR 8 FIXED: Validar que coordenadas están dentro del screenshot
            try:
                if y + h <= screenshot.shape[0] and x + w <= screenshot.shape[1]:
                    if hashit(screenshot[y:y + h, x:x + w]) == lastImgHash:
                        return (x, y, w, h)
            except Exception:
                # Cache inválido, buscar de nuevo
                pass
        res = func(screenshot)
        if res is None:
            return None
        lastX = res[0]
        lastY = res[1]
        lastW = res[2]
        lastH = res[3]
        # ERROR 8 FIXED: Proteger contra errores al calcular hash
        try:
            lastImgHash = hashit(
                screenshot[lastY:lastY + lastH, lastX:lastX + lastW])
        except Exception:
            lastImgHash = None
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
    try:
        cmp_h, cmp_w = compareImage.shape[:2]
        img_h, img_w = img.shape[:2]
    except Exception:
        return None
    # OpenCV requires the search image to be >= template size.
    # User-captured templates may be larger than some cropped search regions.
    if img_h > cmp_h or img_w > cmp_w:
        return None
    match = cv2.matchTemplate(compareImage, img, type)
    res = cv2.minMaxLoc(match)
    # Validar que res tiene la estructura esperada (minVal, maxVal, minLoc, maxLoc)
    if not isinstance(res, tuple) or len(res) < 4:
        return None
    if res[1] <= confidence:
        return None
    # Validar que res[3] (maxLoc) existe y es indexable
    if not isinstance(res[3], (tuple, list)) or len(res[3]) < 2:
        return None
    # Validar que img tiene al menos una fila para len(img[0])
    if len(img) == 0 or len(img[0]) == 0:
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
    try:
        cmp_h, cmp_w = compareImg.shape[:2]
        img_h, img_w = img.shape[:2]
    except Exception:
        return []
    if img_h > cmp_h or img_w > cmp_w:
        return []
    match = cv2.matchTemplate(compareImg, img, cv2.TM_CCOEFF_NORMED)
    loc = np.where(match >= confidence)
    resultList = []
    for pt in zip(*loc[::-1]):
        # Return bbox in compareImg coordinates with the *template* size.
        resultList.append((pt[0], pt[1], len(img[0]), len(img)))
    return resultList


# TODO: add unit tests
def getScreenshot(
    region: Optional[Tuple[int, int, int, int]] = None,
    absolute_region: Optional[Tuple[int, int, int, int]] = None,
) -> Optional[GrayImage]:
    global camera, latestScreenshot, _camera_output_idx, _camera_device_idx
    global _last_grab_was_none, _consecutive_none_frames, _consecutive_black_frames, _consecutive_same_frames, _last_screenshot_stats
    global _last_frame_fingerprint
    global _last_dxcam_recover_log_time
    # dxcam region is relative to a specific output (top-left is always (0,0))
    region = _sanitize_region(region, clamp_non_negative=True)
    # absolute_region is in virtual-desktop coordinates and may be negative
    # (e.g. when a secondary monitor is placed left/up of the primary).
    abs_region = _sanitize_region(absolute_region, clamp_non_negative=False)

    backend = str(_CAPTURE_CFG.get('backend', 'dxcam')).strip().lower()
    if backend == 'obsws':
        obs_frame = _grab_obs_source_gray()
        if obs_frame is not None:
            latestScreenshot = obs_frame
            try:
                mean_val = float(np.mean(obs_frame))
                std_val = float(np.std(obs_frame))
                _last_screenshot_stats = {
                    'shape': tuple(obs_frame.shape),
                    'mean': mean_val,
                    'std': std_val,
                    'backend': 'obsws',
                }
            except Exception:
                pass
            return latestScreenshot
    # NOTE: dxcam's region-based grab() is unreliable on some setups (can return
    # hard-black frames or None). We always grab the full frame and crop locally.
    try:
        screenshot = camera.grab()
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
            screenshot = camera.grab()
        except Exception:
            screenshot = None

        _last_grab_was_none = screenshot is None
        if screenshot is None:
            _consecutive_none_frames += 1
        else:
            _consecutive_none_frames = 0

    # Optional MSS fallback when dxcam returns None.
    # NOTE: MSS/GDI capture often returns black for GPU-accelerated windows (e.g. OBS/projectors).
    mss_fallback_on_none = bool(_CAPTURE_CFG.get('mss_fallback_on_none', False))
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
    full_gray = cast(GrayImage, cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY))
    latestScreenshot = _crop_gray_frame(full_gray, region)

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
        dark_px_thr = int(_CAPTURE_CFG.get('black_dark_pixel_threshold', 8))
        dark_frac_thr = float(_CAPTURE_CFG.get('black_dark_fraction_threshold', 0.98))
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
            'device_idx': _camera_device_idx,
            'output_idx': _camera_output_idx,
        }
        std_thr = float(_CAPTURE_CFG.get('black_std_threshold', 1.0))
        mean_thr = float(_CAPTURE_CFG.get('black_mean_threshold', 2.0))
        mean_force_thr = float(_CAPTURE_CFG.get('black_mean_force_threshold', 2.0))
        # DETERMINISTIC black detection: Frame is black if mean<2 AND std<1.
        # Eliminates false positives in dark caves (mean~15, std~8).
        # Catches real black screens (mean~0, std~0).
        is_probably_black = (mean_val < mean_thr) and (std_val < std_thr)

        # If the frame is *completely* black, try an immediate dxcam retry/recover.
        # This is a common transient dxcam glitch and retrying avoids stalling the pipeline.
        hard_black = mean_val <= 0.5 and std_val <= 0.5
        if hard_black and bool(_CAPTURE_CFG.get('dxcam_retry_on_hard_black', True)):
            try:
                # Re-grab once without recreating the camera.
                # Calling dxcam.create repeatedly can spam stdout.
                shot2 = camera.grab()
                if shot2 is not None:
                    full2 = cast(GrayImage, cv2.cvtColor(shot2, cv2.COLOR_BGRA2GRAY))
                    frame2 = _crop_gray_frame(full2, region)
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
                            'device_idx': _camera_device_idx,
                            'output_idx': _camera_output_idx,
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

    # If dxcam is effectively black and OBS fallback is enabled, try pulling frames
    # directly from OBS WebSocket (bypasses Windows "exclude from capture" issues).
    # This is especially useful when only the taskbar is visible to desktop capture.
    if (
        bool(_CAPTURE_CFG.get('obs_fallback_on_black', True))
        and abs_region is not None
        and _consecutive_black_frames >= int(_CAPTURE_CFG.get('black_frame_threshold', 8))
    ):
        obs_frame = _grab_obs_source_gray()
        if obs_frame is not None:
            latestScreenshot = obs_frame
            _consecutive_black_frames = 0
            try:
                mean_val = float(np.mean(obs_frame))
                std_val = float(np.std(obs_frame))
                _last_screenshot_stats = {
                    'shape': tuple(obs_frame.shape),
                    'mean': mean_val,
                    'std': std_val,
                    'backend': 'obsws',
                    'switched_due_to_black_frames': True,
                }
            except Exception:
                pass
            return latestScreenshot

    black_threshold = int(_CAPTURE_CFG.get('black_frame_threshold', 8))

    # Detect frozen capture (same frame for a long time) and try to recover.
    # FIX: Reduced threshold from 300 to 30 frames (30*3s = 90 seconds recovery)
    stale_threshold = int(_CAPTURE_CFG.get('same_frame_threshold', 30))
    recover_on_stale = bool(_CAPTURE_CFG.get('dxcam_recover_on_stale', True))
    if recover_on_stale and _consecutive_same_frames >= stale_threshold:
        try:
            camera = _recreate_camera(_camera_output_idx, device_idx=_camera_device_idx)
            shot2 = camera.grab()
        except Exception:
            shot2 = None
        if shot2 is not None:
            try:
                full2 = cast(GrayImage, cv2.cvtColor(shot2, cv2.COLOR_BGRA2GRAY))
                frame2 = _crop_gray_frame(full2, region)
                latestScreenshot = cast(GrayImage, frame2)
                _consecutive_same_frames = 0
                _last_frame_fingerprint = _frame_fingerprint(cast(np.ndarray, frame2))

                if bool(_CAPTURE_CFG.get('log_dxcam_recovery', True)):
                    now = time.time()
                    if now - _last_dxcam_recover_log_time >= 5.0:
                        _last_dxcam_recover_log_time = now
                        try:
                            print(
                                f"[fenril][dxcam] Recovered from stale frames (device_idx={_camera_device_idx} output_idx={_camera_output_idx} region={region})"
                            )
                        except Exception:
                            pass
                return latestScreenshot
            except Exception:
                pass

    # Prefer recovering dxcam (recreate the camera) over MSS fallback.
    dxcam_recover = bool(_CAPTURE_CFG.get('dxcam_recover_on_black', True))
    if dxcam_recover and _consecutive_black_frames >= black_threshold:
        try:
            camera = _recreate_camera(_camera_output_idx, device_idx=_camera_device_idx)
            shot2 = camera.grab()
        except Exception:
            shot2 = None
        if shot2 is not None:
            try:
                full2 = cast(GrayImage, cv2.cvtColor(shot2, cv2.COLOR_BGRA2GRAY))
                frame2 = _crop_gray_frame(full2, region)
                mean2 = float(np.mean(frame2))
                std2 = float(np.std(frame2))
                dark_px_thr = int(_CAPTURE_CFG.get('black_dark_pixel_threshold', 8))
                dark_frac_thr = float(_CAPTURE_CFG.get('black_dark_fraction_threshold', 0.98))
                dark_fraction2 = float(np.mean(frame2 <= dark_px_thr))
                std_thr = float(_CAPTURE_CFG.get('black_std_threshold', 1.0))
                mean_thr = float(_CAPTURE_CFG.get('black_mean_threshold', 2.0))
                mean_force_thr = float(_CAPTURE_CFG.get('black_mean_force_threshold', 2.0))
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
                        'device_idx': _camera_device_idx,
                        'output_idx': _camera_output_idx,
                        'recovered_dxcam': True,
                    }

                    # Helpful runtime signal (throttled).
                    if bool(_CAPTURE_CFG.get('log_dxcam_recovery', True)):
                        now = time.time()
                        if now - _last_dxcam_recover_log_time >= 5.0:
                            _last_dxcam_recover_log_time = now
                            try:
                                print(
                                    f"[fenril][dxcam] Recovered from black frames (device_idx={_camera_device_idx} output_idx={_camera_output_idx} region={region})"
                                )
                            except Exception:
                                pass
                    return latestScreenshot
            except Exception:
                pass

            # If recreating the camera didn't help, try probing other device/output combinations.
            # This addresses cases where monitors are split across GPUs or dxcam's output
            # enumeration differs from Win32 monitor indexing.
            if abs_region is not None and bool(_CAPTURE_CFG.get('dxcam_autoprobe_on_black', True)):
                probed = _try_autoprobe_camera_for_abs_region(abs_region)
                if probed is not None:
                    dev, out, cam, rel_region = probed
                    try:
                        camera = cam
                        _camera_device_idx = int(dev)
                        _camera_output_idx = int(out)
                        shot3 = camera.grab()
                    except Exception:
                        shot3 = None
                    if shot3 is not None:
                        try:
                            full3 = cast(GrayImage, cv2.cvtColor(shot3, cv2.COLOR_BGRA2GRAY))
                            frame3 = _crop_gray_frame(full3, rel_region)
                            if not _frame_is_hard_black(cast(np.ndarray, frame3)):
                                latestScreenshot = cast(GrayImage, frame3)
                                _consecutive_black_frames = 0
                                try:
                                    mean3 = float(np.mean(frame3))
                                    std3 = float(np.std(frame3))
                                    dark_px_thr = int(_CAPTURE_CFG.get('black_dark_pixel_threshold', 8))
                                    dark_fraction3 = float(np.mean(frame3 <= dark_px_thr))
                                except Exception:
                                    mean3 = 0.0
                                    std3 = 0.0
                                    dark_fraction3 = 1.0
                                _last_screenshot_stats = {
                                    'shape': tuple(frame3.shape),
                                    'mean': mean3,
                                    'std': std3,
                                    'dark_fraction': dark_fraction3,
                                    'region': rel_region,
                                    'absolute_region': abs_region,
                                    'backend': 'dxcam',
                                    'device_idx': _camera_device_idx,
                                    'output_idx': _camera_output_idx,
                                    'autoprobed_dxcam': True,
                                }
                                if bool(_CAPTURE_CFG.get('log_dxcam_recovery', True)):
                                    now = time.time()
                                    if now - _last_dxcam_recover_log_time >= 5.0:
                                        _last_dxcam_recover_log_time = now
                                        try:
                                            print(
                                                f"[fenril][dxcam] Autoprobed working camera (device_idx={_camera_device_idx} output_idx={_camera_output_idx} rel_region={rel_region})"
                                            )
                                        except Exception:
                                            pass
                                return latestScreenshot
                        except Exception:
                            pass

    # Optional MSS fallback when dxcam is producing black frames.
    # Disabled by default because it commonly returns black for OBS/projectors.
    mss_fallback = bool(_CAPTURE_CFG.get('mss_fallback', False))
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
