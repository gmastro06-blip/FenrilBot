from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


FANDOM_BACKPACKS_URL = "https://tibia.fandom.com/wiki/Backpacks"


@dataclass(frozen=True)
class BackpacksSourceInfo:
    source_url: str
    fetched_at_unix: int


def _data_dir() -> Path:
    return Path(__file__).resolve().parent


def _cache_path() -> Path:
    return _data_dir() / "backpacks.json"


def _default_backpacks() -> list[str]:
    # Minimal offline fallback; UI still works even without network/cache.
    return [
        "Orange Backpack",
        "Red Backpack",
        "Blue Backpack",
        "Yellow Backpack",
        "Brown Backpack",
        "Green Backpack",
        "Grey Backpack",
        "Purple Backpack",
        "Golden Backpack",
        "Parcel",
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


def save_backpacks_cache(names: Iterable[str], *, source_url: str = FANDOM_BACKPACKS_URL) -> Path:
    names_list = _normalize_names(list(names))
    payload = {
        "names": names_list,
        "source": {
            "url": source_url,
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


def fetch_backpacks_from_fandom(*, url: str = FANDOM_BACKPACKS_URL, timeout_s: int = 10) -> list[str]:
    """Fetch backpack item names from the Tibia fandom wiki page.

    This extracts only item names (no descriptions/images) and is meant to
    populate the UI combobox.
    """

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FenrilBot/1.0 (+https://github.com/) Python urllib",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    # Heuristic extraction:
    # - Many relevant links appear as title="<Item Name>".
    # - We keep titles containing 'Backpack' and a couple common container names.
    # Note: This avoids copying page text verbatim; it's just item names.
    titles = re.findall(r'title="([^"]+)"', html)

    candidates: list[str] = []
    for t in titles:
        if "Backpack" in t:
            candidates.append(t)

    # Some commonly used containers are not '... Backpack' but are used by the bot.
    for extra in ("Parcel",):
        if extra in titles:
            candidates.append(extra)

    return _normalize_names(candidates)


def get_backpack_names() -> list[str]:
    """Return backpacks list for UI.

    Resolution order:
    1) Cache file `src/data/backpacks.json` if present
    2) If `FENRIL_BACKPACKS_FETCH=1`, fetch from fandom and write cache
    3) Fallback to a small built-in list
    """

    cached = load_backpacks_cache()
    if cached:
        return cached

    if os.getenv("FENRIL_BACKPACKS_FETCH", "0") in {"1", "true", "True"}:
        try:
            names = fetch_backpacks_from_fandom()
            if names:
                save_backpacks_cache(names)
                return names
        except Exception:
            # Keep UI functional even if network fails.
            pass

    return _default_backpacks()
