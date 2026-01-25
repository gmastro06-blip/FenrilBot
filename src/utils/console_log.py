import time
from typing import Dict, Optional

from src.utils.runtime_settings import get_bool, get_str

_LEVELS: Dict[str, int] = {
    'debug': 10,
    'info': 20,
    'warn': 30,
    'error': 40,
}

_last_by_key: Dict[str, float] = {}

_LOG_LEVEL = get_str({}, '_', env_var='FENRIL_LOG_LEVEL', default='info', prefer_env=True).strip().lower()
_CONSOLE_LOG_ENABLED = get_bool({}, '_', env_var='FENRIL_CONSOLE_LOG', default=True, prefer_env=True)


def configure_console_log(*, level: Optional[str] = None, enabled: Optional[bool] = None) -> None:
    """Configure console logging.

    Defaults come from env vars, but runtime can override via profile config.
    """
    global _LOG_LEVEL, _CONSOLE_LOG_ENABLED
    if level is not None:
        lvl = str(level).strip().lower()
        if lvl not in _LEVELS:
            lvl = 'info'
        _LOG_LEVEL = lvl
    if enabled is not None:
        _CONSOLE_LOG_ENABLED = bool(enabled)


def _level_enabled(level: str) -> bool:
    return _LEVELS.get(level, 20) >= _LEVELS.get(_LOG_LEVEL, 20)


def log(level: str, msg: str) -> None:
    if not _CONSOLE_LOG_ENABLED:
        return
    lvl = level.strip().lower()
    if not _level_enabled(lvl):
        return
    ts = time.strftime('%H:%M:%S')
    print(f"[{ts}][fenril][{lvl}] {msg}")


def log_throttled(key: str, level: str, msg: str, interval_s: float) -> None:
    now = time.time()
    last = _last_by_key.get(key)
    if last is not None and (now - last) < interval_s:
        return
    _last_by_key[key] = now
    log(level, msg)
