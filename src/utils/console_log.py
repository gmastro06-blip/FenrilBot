import os
import time
from typing import Dict

_LEVELS: Dict[str, int] = {
    'debug': 10,
    'info': 20,
    'warn': 30,
    'error': 40,
}

_last_by_key: Dict[str, float] = {}


def _level_enabled(level: str) -> bool:
    configured = os.getenv('FENRIL_LOG_LEVEL', 'info').strip().lower()
    return _LEVELS.get(level, 20) >= _LEVELS.get(configured, 20)


def log(level: str, msg: str) -> None:
    if os.getenv('FENRIL_CONSOLE_LOG', '1') == '0':
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
