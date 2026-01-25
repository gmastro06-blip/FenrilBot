"""Smoke test: click NPC trade Buy/Sell tabs using SetNpcTradeModeTask.

This validates the full runtime path:
- capture via OBS projector (capture window)
- detect trade window + tabs
- click via the bot's mouse backend (action window)
- re-capture and report pixel diffs + write debug images

Usage:
  ./.venv/Scripts/python.exe scripts/smoke_trade_tab_switch.py \
    --capture-title "Proyector en ventana (Fuente) - Tibia_Fuente" \
    --wait-seconds 30

Optional (recommended if your action window title is not already configured in your profile):
  --action-title "Tibia - <charname>"

Outputs:
  debug/smoke_trade_before.png
  debug/smoke_trade_after_buy.png
  debug/smoke_trade_after_sell.png
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
from src.gameplay.core.tasks.setNpcTradeMode import SetNpcTradeModeTask
from src.repositories.refill import core as refillCore
from src.utils.mouse import configure_mouse, get_last_click_backend


def _to_bgr(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def _absdiff_stats(a: np.ndarray, b: np.ndarray) -> tuple[float, float, int]:
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    a2 = a[:h, :w]
    b2 = b[:h, :w]
    diff = cv2.absdiff(a2, b2)
    return float(diff.mean()), float(diff.std()), int(diff.max())


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test trade tab switching")
    parser.add_argument("--capture-title", type=str, required=True)
    parser.add_argument("--action-title", type=str, default=None)
    parser.add_argument("--wait-seconds", type=float, default=30.0)
    parser.add_argument(
        "--force-pyautogui",
        action="store_true",
        help="Force clicks via pyautogui (disables Arduino clicks) for debugging.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    configure_mouse(input_diag=True, disable_arduino_clicks=bool(args.force_pyautogui))

    ctx: dict = {
        "ng_runtime": {
            "capture_window_title": str(args.capture_title),
        }
    }
    if args.action_title:
        ctx["ng_runtime"]["action_window_title"] = str(args.action_title)

    ctx = setTibiaWindowMiddleware(ctx)

    try:
        win = ctx.get('ng_window') if isinstance(ctx.get('ng_window'), dict) else {}
        print('resolved_action_title', win.get('action_resolved_title'))
        print('resolved_capture_title', win.get('capture_resolved_title'))
    except Exception:
        pass

    out_dir = REPO_ROOT / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Wait for trade window to exist in capture.
    deadline = time.time() + float(args.wait_seconds)
    before_gray = None
    top = None
    bot = None

    while time.time() <= deadline:
        ctx = setScreenshotMiddleware(ctx)
        shot = ctx.get("ng_screenshot")
        if shot is None:
            time.sleep(0.25)
            continue
        before_gray = np.asarray(shot)
        try:
            top = refillCore.getTradeTopPosition(before_gray)
            bot = refillCore.getTradeBottomPos(before_gray)
        except Exception:
            top = None
            bot = None
        if top is not None:
            break
        time.sleep(0.25)

    if before_gray is None:
        raise RuntimeError("Failed to capture screenshot")

    cv2.imwrite(str(out_dir / "smoke_trade_before.png"), _to_bgr(before_gray))
    try:
        print('capture_rect', ctx.get('ng_capture_rect'))
        print('action_rect', ctx.get('ng_action_rect'))
    except Exception:
        pass
    print("tradeTop", top)
    print("tradeBottom", bot)

    if top is None:
        raise RuntimeError("Trade window top not detected in capture. Keep NPC trade open and visible in OBS.")

    # Run BUY then SELL.
    for mode in ("buy", "sell"):
        task = SetNpcTradeModeTask(mode)  # type: ignore[arg-type]
        ctx["ng_screenshot"] = before_gray
        task.do(ctx)
        print('click_backend', get_last_click_backend())
        time.sleep(0.35)
        ctx = setScreenshotMiddleware(ctx)
        after = ctx.get("ng_screenshot")
        if after is None:
            raise RuntimeError(f"Failed to capture after {mode}")
        after_gray = np.asarray(after)

        mean, std, mx = _absdiff_stats(before_gray, after_gray)
        print(f"after_{mode}: diff mean={mean:.2f} std={std:.2f} max={mx}")

        cv2.imwrite(str(out_dir / f"smoke_trade_after_{mode}.png"), _to_bgr(after_gray))

        # Use this frame as baseline for the next click.
        before_gray = after_gray

    print("OK: clicks executed; see debug/smoke_trade_*.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
