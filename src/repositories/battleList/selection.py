from __future__ import annotations

from typing import Any, Optional, Tuple

import numpy as np

from src.utils.runtime_settings import get_bool, get_str


def _split_name_list(value: str) -> list[str]:
    if not value:
        return []
    # Support comma/semicolon/newline separated lists.
    raw = value.replace(";", ",").replace("\n", ",").replace("\r", ",")
    out: list[str] = []
    for part in raw.split(","):
        token = part.strip().lower()
        if token:
            out.append(token)
    return out


def _name_matches(name: str, token: str) -> bool:
    if not token:
        return False
    n = (name or "").strip().lower()
    t = token.strip().lower()
    if not n or not t:
        return False
    return n == t or t in n


def choose_target_index(context: Any) -> Tuple[Optional[int], Optional[str], str]:
    """Choose a battle list index to click based on creature names.

    Config (context path or env var):
    - ng_runtime.battlelist_prefer_names / FENRIL_BATTLELIST_PREFER_NAMES
    - ng_runtime.battlelist_ignore_names / FENRIL_BATTLELIST_IGNORE_NAMES

    Returns: (index, creature_name_or_none, reason)
    """

    ng_battle = context.get("ng_battleList", {}) if isinstance(context, dict) else {}
    creatures = ng_battle.get("creatures") if isinstance(ng_battle, dict) else None

    prefer_raw = get_str(
        context,
        "ng_runtime.battlelist_prefer_names",
        env_var="FENRIL_BATTLELIST_PREFER_NAMES",
        default="",
        prefer_env=True,
    )
    ignore_raw = get_str(
        context,
        "ng_runtime.battlelist_ignore_names",
        env_var="FENRIL_BATTLELIST_IGNORE_NAMES",
        default="",
        prefer_env=True,
    )
    prefer = _split_name_list(prefer_raw)
    ignore = _split_name_list(ignore_raw)

    # No parsed creatures -> do NOT click battle list by default.
    # (Clicking index 0 on an empty list leads to "phantom attacking".)
    if creatures is None or not hasattr(creatures, "__len__") or len(creatures) == 0:
        if get_bool(
            context,
            'ng_runtime.battlelist_click_when_empty',
            env_var='FENRIL_BATTLELIST_CLICK_WHEN_EMPTY',
            default=False,
            prefer_env=True,
        ):
            return 0, None, 'default0:no_creatures(click_when_empty)'
        return None, None, 'no_creatures'

    # Convert to plain strings.
    names: list[str] = []
    try:
        for c in creatures:
            try:
                names.append(str(c["name"]))
            except Exception:
                names.append(str(c))
    except Exception:
        # Keep old safety behavior (index 0) only when explicitly allowed.
        if get_bool(
            context,
            'ng_runtime.battlelist_click_when_empty',
            env_var='FENRIL_BATTLELIST_CLICK_WHEN_EMPTY',
            default=False,
            prefer_env=True,
        ):
            return 0, None, 'default0:creatures_iter_error(click_when_empty)'
        return None, None, 'creatures_iter_error'

    def is_ignored(name: str) -> bool:
        if (name or "").strip().lower() in {"unknown"}:
            return True
        return any(_name_matches(name, tok) for tok in ignore)

    # First: try preferred names (ordered by user list).
    for token in prefer:
        for i, name in enumerate(names):
            if is_ignored(name):
                continue
            if _name_matches(name, token):
                return i, name, f"prefer:{token}"

    # Otherwise: first non-ignored entry.
    for i, name in enumerate(names):
        if is_ignored(name):
            continue
        return i, name, "first_nonignored"

    # Everything ignored -> avoid clicking by default.
    if get_bool(
        context,
        'ng_runtime.battlelist_click_when_empty',
        env_var='FENRIL_BATTLELIST_CLICK_WHEN_EMPTY',
        default=False,
        prefer_env=True,
    ):
        return 0, names[0] if names else None, 'default0:all_ignored(click_when_empty)'
    return None, names[0] if names else None, 'all_ignored'
