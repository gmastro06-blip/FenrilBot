"""Preflight: resolve capture/action windows and print diagnostics.

Goal: one fast check before launching the bot, using the persisted profile config in file.json.

Usage:
  ./.venv/Scripts/python.exe scripts/preflight_dual_windows.py

Exits:
  0 = both windows resolved
  2 = could not resolve one/both windows
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, Optional, cast

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware


def _load_enabled_profile_config(file_path: pathlib.Path) -> Dict[str, Any]:
    data = json.loads(file_path.read_text(encoding="utf-8"))

    # This file is a TinyDB export; common layout is {"_default": {"<id>": {"enabled": bool, "config": {...}}}}
    default_table = data.get("_default") if isinstance(data, dict) else None
    if not isinstance(default_table, dict):
        return {}

    for _, row in default_table.items():
        if not isinstance(row, dict):
            continue
        cfg = row.get("config")
        if row.get("enabled") is True and isinstance(cfg, dict):
            return dict(cfg)

    # Fallback: first profile-like row.
    for _, row in default_table.items():
        if not isinstance(row, dict):
            continue
        cfg = row.get("config")
        if isinstance(cfg, dict):
            return dict(cfg)

    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight dual-window resolution")
    parser.add_argument(
        "--no-screenshot",
        action="store_true",
        help="Only resolve window titles; skip capture/screenshot checks.",
    )
    args = parser.parse_args()

    cfg = _load_enabled_profile_config(REPO_ROOT / "file.json")
    raw_ng_runtime = cfg.get("ng_runtime")
    ng_runtime: Dict[str, Any] = dict(raw_ng_runtime) if isinstance(raw_ng_runtime, dict) else {}

    ctx: Dict[str, Any] = {"ng_runtime": dict(ng_runtime)}
    ctx = setTibiaWindowMiddleware(ctx)

    if not args.no_screenshot:
        # Populates ng_capture_rect/ng_action_rect and validates capture pipeline.
        ctx = setScreenshotMiddleware(ctx)

    raw_win = ctx.get("ng_window")
    win: Dict[str, Any] = cast(Dict[str, Any], raw_win) if isinstance(raw_win, dict) else {}

    print("profile.action_window_title", ng_runtime.get("action_window_title"))
    print("profile.capture_window_title", ng_runtime.get("capture_window_title"))
    print("resolved_action_title", win.get("action_resolved_title"))
    print("resolved_capture_title", win.get("capture_resolved_title"))
    print("capture_rect", ctx.get("ng_capture_rect"))
    print("action_rect", ctx.get("ng_action_rect"))
    diag = ctx.get("ng_diag") if isinstance(ctx.get("ng_diag"), dict) else {}
    if diag:
        print("capture_mean", diag.get("capture_mean"))
        print("capture_std", diag.get("capture_std"))

    ok_action = bool(win.get("action_resolved_title"))
    ok_capture = bool(win.get("capture_resolved_title"))

    if not (ok_action and ok_capture):
        print("ERROR: could not resolve one or both windows. Ensure Tibia and the OBS projector are open.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
