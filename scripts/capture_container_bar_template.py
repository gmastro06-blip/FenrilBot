"""Auto-capture a container bar template from a screenshot.

Why
- The bot detects open containers via template matching on container bars.
- If Tibia/OBS scaling changed, existing `containersBars/*.png` templates may no longer match.

This script tries to find an open container grid by locating repeated `empty` slot icons,
then back-computes the container bar top-left using the same offsets the bot uses.

Usage (example)
  python scripts/capture_container_bar_template.py --name "Camouflage Backpack" \
    --image debug/loot_debug_no_loot_backpack_20260127_142458.png

It will write a new template:
  src/repositories/inventory/images/containersBars/Camouflage Backpack v2.png

Notes
- This assumes a standard 4-column container grid with ~32px slots and ~5px gaps.
- If your container is full (no empty slots), it may not find a grid.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional, Tuple

import cv2
import numpy as np


def _nms_points(points: list[tuple[int, int]], *, min_dist: int = 10) -> list[tuple[int, int]]:
    kept: list[tuple[int, int]] = []
    md2 = float(min_dist * min_dist)
    for (x, y) in points:
        ok = True
        for (kx, ky) in kept:
            dx = float(x - kx)
            dy = float(y - ky)
            if (dx * dx + dy * dy) <= md2:
                ok = False
                break
        if ok:
            kept.append((x, y))
    return kept


def _iter_near(x: int, y: int, tol: int) -> Iterable[tuple[int, int]]:
    for yy in range(y - tol, y + tol + 1):
        for xx in range(x - tol, x + tol + 1):
            yield (xx, yy)


def _find_grid_top_left(
    points: list[tuple[int, int]],
    *,
    stride: int,
    tol: int,
) -> Optional[tuple[int, int]]:
    s = set(points)

    def has(x: int, y: int) -> bool:
        for p in _iter_near(x, y, tol):
            if p in s:
                return True
        return False

    best = None
    best_score = -1

    for (x, y) in points:
        # Require at least 3 columns and 2 rows worth of empty slots.
        row_hits = sum(1 for k in range(1, 4) if has(x + k * stride, y))
        col_hits = sum(1 for k in range(1, 3) if has(x, y + k * stride))
        score = row_hits * 10 + col_hits
        if row_hits >= 2 and col_hits >= 1 and score > best_score:
            best = (x, y)
            best_score = score

    return best


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a containersBars template from a screenshot")
    parser.add_argument("--name", required=True, help="Canonical container name (e.g., 'Camouflage Backpack')")
    parser.add_argument("--image", required=True, help="Path to a screenshot where the container is open")
    parser.add_argument("--suffix", default="v2", help="Suffix to add to the output filename")
    parser.add_argument("--threshold", type=float, default=0.97, help="Empty-slot match threshold")
    parser.add_argument(
        "--roi-right-frac",
        type=float,
        default=0.0,
        help=(
            "If >0, only search the right-side fraction of the image (e.g. 0.30 means rightmost 30%). "
            "Useful to avoid false matches in the game window."
        ),
    )
    parser.add_argument("--stride", type=int, default=37, help="Expected slot stride (slot+gap)")
    parser.add_argument("--tol", type=int, default=3, help="Stride tolerance in pixels")
    parser.add_argument("--bar-width", type=int, default=94)
    parser.add_argument("--bar-height", type=int, default=12)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    img_path = Path(args.image)
    if not img_path.is_absolute():
        img_path = (repo / img_path).resolve()

    screenshot = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if screenshot is None:
        raise SystemExit(f"Could not read screenshot: {img_path}")

    empty_tpl_path = repo / "src" / "repositories" / "inventory" / "images" / "slots" / "empty.png"
    empty_tpl = cv2.imread(str(empty_tpl_path), cv2.IMREAD_GRAYSCALE)
    if empty_tpl is None:
        raise SystemExit(f"Could not read template: {empty_tpl_path}")

    offset_x = 0
    if float(args.roi_right_frac) > 0.0:
        frac = float(args.roi_right_frac)
        frac = max(0.0, min(frac, 1.0))
        offset_x = int(screenshot.shape[1] * (1.0 - frac))
        screenshot_roi = screenshot[:, offset_x:]
    else:
        screenshot_roi = screenshot

    res = cv2.matchTemplate(screenshot_roi, empty_tpl, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(res >= float(args.threshold))
    if len(xs) == 0:
        raise SystemExit(
            f"No empty slots found at threshold {args.threshold}. "
            "Open a container with at least a few empty slots and try again."
        )

    # Sort by score descending for better NMS.
    scored = sorted(
        ((int(x) + offset_x, int(y), float(res[int(y), int(x)])) for (y, x) in zip(ys, xs)),
        key=lambda t: t[2],
        reverse=True,
    )
    points = _nms_points([(x, y) for (x, y, _s) in scored], min_dist=10)

    print(f"empty-slot matches: raw={len(scored)} nms={len(points)} threshold={args.threshold}")
    if len(points) < 5:
        print("sample points:", points[:10])

    # Estimate typical stride by looking at nearest neighbors in roughly the same row/col.
    dxs: list[int] = []
    dys: list[int] = []
    for (x, y) in points:
        # row neighbors
        row = [(xx, yy) for (xx, yy) in points if abs(yy - y) <= 3 and xx > x]
        if row:
            nn = min(row, key=lambda p: p[0])
            dxs.append(int(nn[0] - x))
        col = [(xx, yy) for (xx, yy) in points if abs(xx - x) <= 3 and yy > y]
        if col:
            nn = min(col, key=lambda p: p[1])
            dys.append(int(nn[1] - y))

    def _top_counts(vals: list[int]) -> list[tuple[int, int]]:
        from collections import Counter

        c = Counter(vals)
        return c.most_common(8)

    if dxs:
        print("dx candidates:", _top_counts(dxs))
    if dys:
        print("dy candidates:", _top_counts(dys))

    top_left = _find_grid_top_left(points, stride=int(args.stride), tol=int(args.tol))
    if top_left is None:
        raise SystemExit(
            "Could not infer a 4-col grid from empty slots. "
            "Try lowering --threshold slightly or ensure the container grid is visible."
        )

    slot0_x, slot0_y = top_left
    bar_x = int(slot0_x - 10)
    bar_y = int(slot0_y - 18)

    bw = int(args.bar_width)
    bh = int(args.bar_height)
    bar_x = max(0, min(bar_x, screenshot.shape[1] - bw))
    bar_y = max(0, min(bar_y, screenshot.shape[0] - bh))

    crop = screenshot[bar_y : bar_y + bh, bar_x : bar_x + bw]

    out_dir = repo / "src" / "repositories" / "inventory" / "images" / "containersBars"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{args.name} {args.suffix}.png" if args.suffix else f"{args.name}.png"
    out_path = out_dir / out_name

    ok = cv2.imwrite(str(out_path), crop)
    if not ok:
        raise SystemExit(f"Failed to write: {out_path}")

    print(f"Wrote: {out_path}")
    print(f"Grid slot0: {(slot0_x, slot0_y)} -> bar: {(bar_x, bar_y)} size {(bw, bh)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
