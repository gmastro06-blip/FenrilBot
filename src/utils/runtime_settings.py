from __future__ import annotations

import os
from typing import Any, Mapping, Optional


_TRUE = {"1", "true", "yes", "y", "on", "t"}
_FALSE = {"0", "false", "no", "n", "off", "f"}


def _get_nested(mapping: Any, path: str) -> Any:
    cur: Any = mapping
    for part in path.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
    return cur


def _parse_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
    return None


def get_bool(
    context: Any,
    path: str,
    *,
    env_var: Optional[str] = None,
    default: bool = False,
) -> bool:
    """Get a boolean setting from context (preferred) or env var (fallback)."""

    value = _get_nested(context, path)
    parsed = _parse_bool(value)
    if parsed is not None:
        return parsed

    if env_var:
        env = os.getenv(env_var)
        parsed = _parse_bool(env)
        if parsed is not None:
            return parsed

    return default


def get_float(
    context: Any,
    path: str,
    *,
    env_var: Optional[str] = None,
    default: float,
) -> float:
    value = _get_nested(context, path)
    if value is not None:
        try:
            return float(value)
        except Exception:
            pass
    if env_var:
        env = os.getenv(env_var)
        if env is not None:
            try:
                return float(env)
            except Exception:
                pass
    return default


def get_str(
    context: Any,
    path: str,
    *,
    env_var: Optional[str] = None,
    default: str = "",
) -> str:
    value = _get_nested(context, path)
    if value is not None:
        try:
            return str(value)
        except Exception:
            pass
    if env_var:
        env = os.getenv(env_var)
        if env is not None:
            return env
    return default
