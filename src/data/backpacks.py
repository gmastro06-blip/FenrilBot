from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class BackpacksSourceInfo:
    source: str
    fetched_at_unix: int


def _data_dir() -> Path:
    return Path(__file__).resolve().parent


def _cache_path() -> Path:
    return _data_dir() / "backpacks.json"


def _default_backpacks() -> list[str]:
    # Minimal offline fallback; UI still works even without network/cache.
    # IMPORTANTE: Estos nombres deben coincidir con los templates en src/repositories/inventory/config.py
    return [
        "25 Years Backpack",
        "Anniversary Backpack",
        "Beach Backpack",
        "Birthday Backpack",
        "Brocade Backpack",
        "Buggy Backpack",
        "Cake Backpack",
        "Camouflage Backpack",
        "Crown Backpack",
        "Crystal Backpack",
        "Deepling Backpack",
        "Demon Backpack",
        "Dragon Backpack",
        "Expedition Backpack",
        "Fur Backpack",
        "Glooth Backpack",
        "Golden Backpack",
        "Green Backpack",
        "Heart Backpack",
        "Minotaur Backpack",
        "Moon Backpack",
        "Mushroom Backpack",
        "Pannier Backpack",
        "Pirate Backpack",
        "Raccoon Backpack",
        "Red Backpack",
        "Santa Backpack",
        "Wolf Backpack",
    ]


def load_backpacks_cache() -> list[str] | None:
    path = _cache_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    names = payload.get("names") if isinstance(payload, dict) else None
    if not isinstance(names, list):
        return None

    out: list[str] = []
    for n in names:
        if isinstance(n, str) and n.strip():
            out.append(n.strip())

    return _normalize_names(out)


def save_backpacks_cache(names: Iterable[str], *, source: str = "manual") -> Path:
    names_list = _normalize_names(list(names))
    payload = {
        "names": names_list,
        "source": {
            "source": source,
            "fetched_at_unix": int(time.time()),
        },
    }
    path = _cache_path()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _normalize_names(names: List[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    for name in names:
        name = name.strip()
        if not name:
            continue
        # Filter obvious non-items / page titles.
        if name in {"Backpacks", "Backpack"}:
            continue

        if name not in seen:
            seen.add(name)
            out.append(name)

    out.sort(key=str.casefold)
    return out


def get_backpack_names() -> list[str]:
    """Return backpacks list for UI.

    Resolution order:
    1) Cache file `src/data/backpacks.json` if present
    2) Fallback to a small built-in list
    """

    cached = load_backpacks_cache()
    if cached:
        return cached

    return _default_backpacks()
