"""Normalize inventory slot template PNGs.

Goal
- Ensure user-provided icon PNGs match the exact pixel size of existing inventory slot templates.
- Optionally crop/pad to target size, preserving the icon centered.
- Save into `src/repositories/inventory/images/slots/` with a given name prefix.

Why
The bot uses exact image hashing (after conversion to grayscale). If template sizes differ,
hashing and lookup will not match.

Usage examples (PowerShell)
- Normalize three downloaded vial icons:
  `python scripts/normalize_slot_templates.py --prefix "empty vial" --in "C:/path/vial1.png" "C:/path/vial2.png" "C:/path/vial3.png"`

- Normalize everything in a folder:
  `python scripts/normalize_slot_templates.py --prefix "empty vial" --glob "C:/path/to/icons/*.png"`

Notes
- This script DOES NOT download assets from the internet.
- It only transforms images you already have locally.
"""

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
SLOTS_DIR = REPO_ROOT / "src" / "repositories" / "inventory" / "images" / "slots"
REFERENCE_TEMPLATE = SLOTS_DIR / "small empty potion flask.png"


def _iter_inputs(paths: Sequence[str], patterns: Sequence[str]) -> List[Path]:
    out: List[Path] = []
    for path_str in paths:
        if not path_str:
            continue
        out.append(Path(path_str))
    for pat in patterns:
        if not pat:
            continue
        for match in glob.glob(pat):
            out.append(Path(match))
    # Deduplicate while preserving order
    seen = set()
    unique: List[Path] = []
    for path in out:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _center_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = img.size
    if w == target_w and h == target_h:
        return img
    left = max(0, (w - target_w) // 2)
    top = max(0, (h - target_h) // 2)
    right = left + min(target_w, w)
    bottom = top + min(target_h, h)
    cropped = img.crop((left, top, right, bottom))
    # If source smaller than target in any dimension, pad after crop
    if cropped.size != (target_w, target_h):
        canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        ox = (target_w - cropped.size[0]) // 2
        oy = (target_h - cropped.size[1]) // 2
        canvas.paste(cropped, (ox, oy), cropped)
        return canvas
    return cropped


def normalize_one(src: Path, target_size: Tuple[int, int]) -> Image.Image:
    img: Image.Image = Image.open(src).convert("RGBA")
    return _center_crop(img, target_size[0], target_size[1])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize slot template PNGs to the bot's expected size.")
    parser.add_argument(
        "--prefix",
        required=True,
        help="Output filename prefix inside slots folder (e.g. 'empty vial').",
    )
    parser.add_argument(
        "--select",
        action="store_true",
        help="Open a file picker to select input PNGs (ignores --in/--glob).",
    )
    parser.add_argument(
        "--in",
        dest="inputs",
        nargs="*",
        default=[],
        help="One or more input PNG paths.",
    )
    parser.add_argument(
        "--glob",
        dest="globs",
        nargs="*",
        default=[],
        help="One or more glob patterns for input PNGs.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(SLOTS_DIR),
        help="Output directory (defaults to inventory slots folder).",
    )
    parser.add_argument(
        "--ref",
        default=str(REFERENCE_TEMPLATE),
        help="Reference template path to copy size from (defaults to small empty potion flask).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without creating files.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    out_dir = Path(args.out_dir)
    ref_path = Path(args.ref)

    if not ref_path.exists():
        raise FileNotFoundError(f"Reference template not found: {ref_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    ref_img = Image.open(ref_path).convert("RGBA")
    target_size = ref_img.size  # (w, h)

    if args.select:
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()
            try:
                root.wm_attributes('-topmost', 1)
            except Exception:
                pass
            try:
                root.lift()
                root.update()
            except Exception:
                pass

            selected = filedialog.askopenfilenames(
                title='Select PNG icon(s) to normalize',
                filetypes=[('PNG images', '*.png')],
                parent=root,
            )
            try:
                root.destroy()
            except Exception:
                pass
            inputs = [Path(p) for p in selected]
        except Exception as e:
            print(f"Failed to open file picker: {type(e).__name__}: {e}")
            inputs = []

        # Fallback: allow pasting paths if the dialog is unavailable/hidden.
        if not inputs:
            print('No files selected (dialog canceled/hidden) or file picker unavailable.')
            print('Paste one or more full PNG paths, separated by semicolons, then press Enter.')
            print('Or press Enter to abort.')
            try:
                line = input('paths> ').strip()
            except Exception:
                line = ''
            if line:
                parts = [p.strip().strip('"') for p in line.split(';') if p.strip()]
                inputs = [Path(p) for p in parts]
    else:
        inputs = _iter_inputs(args.inputs, args.globs)

    if not inputs:
        print("No inputs provided. Use --select or --in/--glob.")
        return 2

    # Normalize and save
    written = 0
    for i, src in enumerate(inputs, start=1):
        if not src.exists():
            print(f"[skip] missing: {src}")
            continue

        normalized = normalize_one(src, target_size)
        out_name = f"{args.prefix} {i}.png"
        out_path = out_dir / out_name

        if args.dry_run:
            print(f"[dry-run] {src} -> {out_path} (size {normalized.size})")
            continue

        normalized.save(out_path)
        print(f"[ok] {src} -> {out_path} (size {normalized.size})")
        written += 1

    if written == 0 and not args.dry_run:
        print("No files written.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
