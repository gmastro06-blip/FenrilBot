import math
from typing import Optional

from src.utils.runtime_settings import get_bool

SAFE_LOG_ENABLED = get_bool({}, '_', env_var='FENRIL_SAFE_LOG', default=False, prefer_env=True)


def configure_safe_log(*, enabled: Optional[bool] = None) -> None:
    """Configure whether safety telemetry logs are printed.

    Default comes from env var, but runtime can override via config.
    """
    global SAFE_LOG_ENABLED
    if enabled is None:
        return
    SAFE_LOG_ENABLED = bool(enabled)


def _log_invalid(label: str, value: object, reason: str) -> None:
    if not SAFE_LOG_ENABLED:
        return
    prefix = "telemetry" if label else "value"
    print(f"[safety] {prefix} '{label}' invalid ({reason}): {value!r}")


def safe_int(value: object, label: str = "") -> Optional[int]:
    if value is None:
        _log_invalid(label, value, "none")
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            _log_invalid(label, value, "nan_or_inf")
            return None
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            _log_invalid(label, value, "empty")
            return None
        try:
            return int(float(stripped))
        except ValueError:
            _log_invalid(label, value, "not_numeric")
            return None
    _log_invalid(label, value, "unsupported_type")
    return None


def safe_float(value: object, label: str = "") -> Optional[float]:
    if value is None:
        _log_invalid(label, value, "none")
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        value_float = float(value)
        if math.isnan(value_float) or math.isinf(value_float):
            _log_invalid(label, value, "nan_or_inf")
            return None
        return value_float
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            _log_invalid(label, value, "empty")
            return None
        try:
            return float(stripped)
        except ValueError:
            _log_invalid(label, value, "not_numeric")
            return None
    _log_invalid(label, value, "unsupported_type")
    return None
