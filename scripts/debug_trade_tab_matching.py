"""Debug helper: verify NPC trade window + Buy/Sell tab template matching.

- Captures one frame from the bot capture pipeline (OBS projector).
- Detects trade window using refillCore.getTradeTopPosition/getTradeBottomPos.
- Searches for BUY/SELL tab templates inside the trade window ROI.
- Writes an annotated debug image to debug/trade_tabs_match_debug.png

Usage:
  ./.venv/Scripts/python.exe scripts/debug_trade_tab_matching.py \
    --capture-title "Proyector en ventana (Fuente) - Tibia_Fuente"
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
from typing import Optional

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2

from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware
from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.repositories.refill import core as refillCore
from src.repositories.refill.config import tradeTabsImages
from src.utils.core import locateMultiScale


def _draw_box(bgr: np.ndarray, box: tuple[int, int, int, int], color: tuple[int, int, int], label: str) -> None:
    x, y, w, h = box
    cv2.rectangle(bgr, (x, y), (x + w, y + h), color, 2)
    cv2.putText(
        bgr,
        label,
        (x, max(0, y - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Debug trade tab matching")
    parser.add_argument(
        "--capture-title",
        type=str,
        required=True,
        help="OBS projector (capture) window title substring/exact title",
    )
    parser.add_argument(
        "--action-title",
        type=str,
        default=None,
        help="Tibia (action) window title substring/exact title (optional)",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=8.0,
        help="How long to poll for the trade window to appear before failing.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    ctx: dict = {
        "ng_runtime": {
            "capture_window_title": str(args.capture_title),
        }
    }
    if args.action_title:
        ctx["ng_runtime"]["action_window_title"] = str(args.action_title)

    ctx = setTibiaWindowMiddleware(ctx)

    out_dir = REPO_ROOT / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)

    gray = None
    dbg_bgr = None
    top = None
    bot = None

    deadline = time.time() + float(args.wait_seconds)
    attempt = 0
    while time.time() <= deadline:
        attempt += 1
        ctx = setScreenshotMiddleware(ctx)
        shot = ctx.get("ng_screenshot")
        if shot is None:
            time.sleep(0.25)
            continue

        img = np.asarray(shot)
        if img.ndim == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            dbg_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            gray = img
            dbg_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        try:
            top = refillCore.getTradeTopPosition(gray)
            bot = refillCore.getTradeBottomPos(gray)
        except Exception:
            top = None
            bot = None

        if top is not None or bot is not None:
            print(f"[attempt {attempt}] capture", gray.shape, "mean", float(gray.mean()), "std", float(gray.std()))
            print("tradeTop", top)
            print("tradeBottom", bot)
            break

        time.sleep(0.25)

    if gray is None or dbg_bgr is None:
        raise RuntimeError("Failed to capture screenshot")

    raw_fp = out_dir / "trade_tabs_match_frame.png"
    cv2.imwrite(str(raw_fp), dbg_bgr)
    print("wrote", raw_fp)

    # If still not detected, dump and fail.
    if top is None and bot is None:
        print("tradeTop", top)
        print("tradeBottom", bot)
        fp = out_dir / "trade_tabs_match_failed_no_trade_window.png"
        cv2.imwrite(str(fp), dbg_bgr)
        print("wrote", fp)
        return 2

    if top is None or bot is None:
        fp = out_dir / "trade_tabs_match_failed_no_trade_window.png"
        cv2.imwrite(str(fp), dbg_bgr)
        print("wrote", fp)
        return 2

    tx, ty, tw, th = map(int, top)
    bx, by, bw, bh = map(int, bot)

    _draw_box(dbg_bgr, (tx, ty, tw, th), (255, 0, 255), "tradeTop")
    _draw_box(dbg_bgr, (bx, by, bw, bh), (0, 255, 255), "tradeBottom")

    # Build a trade ROI that contains the tabs.
    x0 = tx
    y0 = ty
    x1 = min(gray.shape[1], tx + max(360, tw))
    y1 = min(gray.shape[0], by + 90)

    cv2.rectangle(dbg_bgr, (x0, y0), (x1, y1), (0, 255, 0), 2)
    cv2.putText(
        dbg_bgr,
        "tradeROI",
        (x0, max(0, y0 - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )

    trade_roi = gray[y0:y1, x0:x1]

    scales = (0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25)

    missing: list[str] = []
    for mode in ("buy", "sell"):
        templates = tradeTabsImages.get(mode) or []
        if not templates:
            print(mode, "no templates")
            missing.append(mode)
            continue

        found = None
        for i, templ in enumerate(templates):
            pos = locateMultiScale(trade_roi, templ, confidence=0.70, scales=scales)
            if pos is not None:
                found = pos
                print(mode, f"found template[{i}]", pos)
                break

        if found is None:
            print(mode, "NOT FOUND")
            missing.append(mode)
            continue

        x, y, w, h = map(int, found)
        fx, fy = x0 + x, y0 + y
        color = (255, 0, 0) if mode == "buy" else (0, 0, 255)
        _draw_box(dbg_bgr, (fx, fy, w, h), color, mode)

    fp = out_dir / "trade_tabs_match_debug.png"
    cv2.imwrite(str(fp), dbg_bgr)
    print("wrote", fp)

    # Fallback: global search to verify whether the tabs exist anywhere in the capture.
    if missing:
        print("--- global search fallback ---")
        for mode in list(missing):
            templates = tradeTabsImages.get(mode) or []
            global_found: Optional[tuple[int, tuple[int, int, int, int]]] = None
            for i, templ in enumerate(templates):
                pos = locateMultiScale(gray, templ, confidence=0.70, scales=scales)
                if pos is not None:
                    global_found = (i, pos)
                    break
            print(mode, "global", global_found)

        fp2 = out_dir / "trade_tabs_match_debug_global.png"
        # annotate global matches (if any) on a copy
        dbg2 = dbg_bgr.copy()
        for mode in ("buy", "sell"):
            templates = tradeTabsImages.get(mode) or []
            best_global: Optional[tuple[int, tuple[int, int, int, int]]] = None
            for i, templ in enumerate(templates):
                pos = locateMultiScale(gray, templ, confidence=0.70, scales=scales)
                if pos is not None:
                    best_global = (i, pos)
                    break
            if best_global is None:
                continue
            _, (x, y, w, h) = best_global
            color = (255, 0, 0) if mode == "buy" else (0, 0, 255)
            _draw_box(dbg2, (int(x), int(y), int(w), int(h)), color, f"{mode}.global")
        cv2.imwrite(str(fp2), dbg2)
        print("wrote", fp2)

    if missing:
        print("missing", missing)
        return 3

    print("OK: found buy+sell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
