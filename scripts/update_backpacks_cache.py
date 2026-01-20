"""Refresh the backpacks list cache used by the UI.

Usage (PowerShell):
  $env:FENRIL_BACKPACKS_FETCH='1'
  ./.venv/Scripts/python.exe ./scripts/update_backpacks_cache.py

This will write/update `src/data/backpacks.json`.
"""

from __future__ import annotations

from src.data.backpacks import fetch_backpacks_from_fandom, save_backpacks_cache


def main() -> None:
    names = fetch_backpacks_from_fandom()
    path = save_backpacks_cache(names)
    print(f"Wrote {len(names)} backpacks to {path}")


if __name__ == "__main__":
    main()
