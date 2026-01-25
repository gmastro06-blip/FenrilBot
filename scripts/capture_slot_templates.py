"""Capture inventory slot template PNGs in the exact size the bot expects.

This script uses `src.tools.slot_template_capturer.SlotTemplateCapturer`.

Prerequisites
- Your capture is working (same as running the bot):
  - If you use OBS projector capture, set `FENRIL_CAPTURE_WINDOW_TITLE`.
  - Otherwise set `FENRIL_OUTPUT_IDX` and make sure Tibia is visible.

Recommended workflow
1) Open your MAIN backpack.
2) Put the items you want to capture in the first slots (slot indexes 0, 1, 2...).
3) Run:
   python scripts/capture_slot_templates.py --backpack "backpack bottom" --prefix "empty vial" --slots 0 1 2

Output
- Writes to `src/repositories/inventory/images/slots/` by default.
- Produces `"<prefix> 1.png"`, `"<prefix> 2.png"`, ...

NOTE
- This script does NOT download images from the internet.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware
from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.tools.slot_template_capturer import SlotTemplateCapturer


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "src" / "repositories" / "inventory" / "images" / "slots"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture slot templates as bot-sized PNGs")
    parser.add_argument("--backpack", default="backpack bottom", help="Backpack bar template key (inventory containersBars)")
    parser.add_argument("--prefix", required=True, help="Output filename prefix (e.g. 'empty vial')")
    parser.add_argument("--slots", nargs="*", type=int, default=[0, 1, 2], help="Slot indices to capture")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--output-idx", type=int, default=None, help="Force dxcam output index")
    parser.add_argument(
        "--capture-title",
        type=str,
        default=None,
        help="OBS projector (capture) window title substring or exact title. If omitted, uses env FENRIL_CAPTURE_WINDOW_TITLE or auto-detect.",
    )
    parser.add_argument(
        "--action-title",
        type=str,
        default=None,
        help="Tibia (action) window title substring or exact title. Optional for capture-only, but helps dual-window setups.",
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="Optional capture region as 'left,top,right,bottom' relative to output (advanced)",
    )
    args = parser.parse_args()

    region = None
    if args.region:
        parts = [p.strip() for p in str(args.region).split(",") if p.strip()]
        if len(parts) == 4:
            region = (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))

    # OBS projector / dual-window: use the same middleware chain as the bot
    # to resolve capture window + dxcam output idx + region.
    if args.capture_title:
        os.environ['FENRIL_CAPTURE_WINDOW_TITLE'] = str(args.capture_title)
    if args.action_title:
        os.environ['FENRIL_ACTION_WINDOW_TITLE'] = str(args.action_title)

    context: dict = {}
    context = setTibiaWindowMiddleware(context)
    context = setScreenshotMiddleware(context)

    screenshot = context.get('ng_screenshot')
    if screenshot is None:
        raise RuntimeError('Failed to capture screenshot. Check OBS projector is visible and titles match.')

    capture_region = context.get('ng_capture_region')
    capture_abs = context.get('ng_capture_absolute_region')
    capture_output_idx = context.get('ng_capture_output_idx')

    # If user specified an explicit region, prefer it.
    if region is not None:
        capture_region = region

    capturer = SlotTemplateCapturer(
        args.backpack,
        out_dir=Path(args.out_dir),
        capture_region=capture_region,
        capture_absolute_region=capture_abs,
        output_idx=args.output_idx if args.output_idx is not None else capture_output_idx,
    )

    results = capturer.capture_to_files(prefix=str(args.prefix), slot_indices=list(args.slots), screenshot=screenshot)

    print("\nCaptured:")
    for r in results:
        print(f"- slot={r.slot_index} -> {r.out_path} shape={r.image_shape}")

    print("\nTip: if hashes don't match, ensure capture scaling is 100% and the backpack is fully visible.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
