"""Write/update the backpacks list cache used by the UI (offline).

This script no longer fetches anything from the web. Provide names locally.

Usage (PowerShell):
  # From a text file (one name per line)
  ./.venv/Scripts/python.exe -u ./scripts/update_backpacks_cache.py --from-file .\backpacks.txt

  # Or inline
  ./.venv/Scripts/python.exe -u ./scripts/update_backpacks_cache.py --names "Orange Backpack,Red Backpack,Parcel"

This writes/updates `src/data/backpacks.json`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.data.backpacks import save_backpacks_cache


def main() -> None:
    parser = argparse.ArgumentParser(description='Update backpacks cache (offline)')
    parser.add_argument('--from-file', type=str, default=None, help='Path to text file (one backpack name per line)')
    parser.add_argument('--names', type=str, default=None, help='Comma-separated backpack names')
    args = parser.parse_args()

    names: list[str] = []
    if args.from_file:
        p = Path(args.from_file)
        raw = p.read_text(encoding='utf-8', errors='replace').splitlines()
        names.extend([line.strip() for line in raw if line.strip()])
    if args.names:
        names.extend([n.strip() for n in args.names.split(',') if n.strip()])

    if not names:
        raise SystemExit('No names provided. Use --from-file or --names.')

    path = save_backpacks_cache(names, source='manual')
    print(f"Wrote {len(names)} backpacks to {path}")


if __name__ == "__main__":
    main()
