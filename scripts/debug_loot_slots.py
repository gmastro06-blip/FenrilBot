import argparse
import pathlib
import time
from typing import Optional

import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.repositories.inventory.core import images as inv_images
from src.utils.core import locateMultiple


def _latest_debug_png(debug_dir: pathlib.Path) -> Optional[pathlib.Path]:
    files = sorted(debug_dir.glob("loot_debug_*_*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _bbox_close(a: tuple[int, int, int, int], b: tuple[int, int, int, int], tol: int = 10) -> bool:
    return (
        abs(a[0] - b[0]) <= tol
        and abs(a[1] - b[1]) <= tol
        and abs(a[2] - b[2]) <= tol
        and abs(a[3] - b[3]) <= tol
    )


def _subtract(after: list[tuple[int, int, int, int]], before: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    out: list[tuple[int, int, int, int]] = []
    for a in after:
        if any(_bbox_close(a, b) for b in before):
            continue
        out.append(a)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Annotate empty-slot detections on a loot debug screenshot.")
    parser.add_argument("--in", dest="inp", default="", help="Input PNG path (default: latest debug/loot_debug_*.png)")
    parser.add_argument("--out", dest="out", default="", help="Output PNG path (default: debug/loot_slots_annotated_<ts>.png)")
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    debug_dir = root / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    in_path = pathlib.Path(args.inp) if args.inp else _latest_debug_png(debug_dir)
    if not in_path or not in_path.exists():
        print("No input PNG found.")
        return 2

    img = cv2.imread(str(in_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("Failed to read", in_path)
        return 3

    empty_tpl = inv_images.get("slots", {}).get("empty")
    if empty_tpl is None:
        print("Missing slots/empty template")
        return 4

    # For a single static screenshot we can't do true before/after, but we can still show all empties.
    empties = locateMultiple(img, empty_tpl, confidence=0.86)

    bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    for (x, y, w, h) in empties:
        cv2.rectangle(bgr, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 255), 1)

    # Show cluster buckets (same as CollectDeadCorpse heuristic)
    clusters: dict[tuple[int, int], list[tuple[int, int, int, int]]] = {}
    cell = 220
    for b in empties:
        key = (int(b[0]) // cell, int(b[1]) // cell)
        clusters.setdefault(key, []).append(b)
    if clusters:
        best = max(clusters.values(), key=lambda v: len(v))
        for (x, y, w, h) in best:
            cv2.rectangle(bgr, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 2)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = pathlib.Path(args.out) if args.out else (debug_dir / f"loot_slots_annotated_{ts}.png")
    cv2.imwrite(str(out_path), np.ascontiguousarray(bgr))

    print("in:", in_path)
    print("out:", out_path)
    print("empties:", len(empties), "clusters:", len(clusters))
    if clusters:
        print("best_cluster_size:", len(max(clusters.values(), key=lambda v: len(v))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
