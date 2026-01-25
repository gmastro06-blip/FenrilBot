"""List open window titles to help configure action/capture window selection.

Usage:
  ./.venv/Scripts/python.exe scripts/list_windows_titles.py

This prints non-empty titles and a few common filters (Tibia / OBS projector).
"""

from __future__ import annotations

import re

import pygetwindow as gw


def main() -> int:
    titles = [t for t in gw.getAllTitles() if t and t.strip()]
    print(f"total_titles={len(titles)}")

    def show(label: str, pattern: str) -> None:
        rx = re.compile(pattern, re.IGNORECASE)
        hits = [t for t in titles if rx.search(t)]
        print(f"\n[{label}] {len(hits)}")
        for t in hits[:50]:
            print(f"- {t}")
        if len(hits) > 50:
            print(f"... ({len(hits)-50} more)")

    show("tibia", r"tibia")
    show("obs_projector", r"proyector en ventana|projector")

    print("\n[all] (first 80)")
    for t in titles[:80]:
        print(f"- {t}")
    if len(titles) > 80:
        print(f"... ({len(titles)-80} more)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
