from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verifies that slot template PNGs are being loaded into the inventory slot hash map. "
            "Useful after adding templates like 'empty vial*.png'."
        )
    )
    parser.add_argument(
        "--prefix",
        default="empty vial",
        help="Filename prefix to filter (default: 'empty vial').",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    slots_dir = repo_root / "src" / "repositories" / "inventory" / "images" / "slots"

    # Ensure imports like `from src...` work when executed as a standalone script.
    sys.path.insert(0, str(repo_root))

    # Import after computing paths so the script still reports helpful errors.
    from src.repositories.inventory import config as inv_config  # noqa: PLC0415

    pattern = str(slots_dir / f"{args.prefix}*.png")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No files found for pattern: {pattern}")
        return 1

    print(f"Slots dir: {slots_dir}")
    print(f"Found {len(files)} file(s) matching '{args.prefix}*.png'\n")

    from src.utils.core import hashit  # noqa: PLC0415
    from src.utils.image import loadFromRGBToGray  # noqa: PLC0415

    missing = 0
    for fp in files:
        filename = os.path.basename(fp)
        try:
            img = loadFromRGBToGray(fp)
            h = hashit(img)
        except Exception as e:
            print(f"FAILED TO LOAD: {filename} ({e})")
            missing += 1
            continue

        mapped = inv_config.slotsImagesHashes.get(h)
        if not mapped:
            print(f"MISSING HASH: {filename}")
            missing += 1
            continue

        print(f"OK: {filename} -> {mapped}")

    if missing:
        print(f"\n{missing} file(s) were not recognized (hash not present).")
        return 2

    print("\nAll matching templates are loaded and mapped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
