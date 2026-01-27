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
from typing import List
from typing import Any, Dict, Optional, cast

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.esc_stop import install_esc_stop

# Allow aborting any preflight run with ESC.
install_esc_stop(exit_process=True)

from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware


def _list_window_titles() -> List[str]:
    """Return a list of visible top-level window titles (best-effort)."""
    titles: List[str] = []
    try:
        import win32gui

        def _enum(hwnd: int, _param: object) -> None:
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if title and title.strip():
                    titles.append(str(title))
            except Exception:
                return

        win32gui.EnumWindows(_enum, None)
    except Exception:
        return titles
    # Stable-ish output: sort case-insensitively.
    titles.sort(key=lambda s: s.lower())
    return titles


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
    parser.add_argument(
        "--list-windows",
        action="store_true",
        help="Print current top-level window titles (helps configuring action/capture titles).",
    )
    args = parser.parse_args()

    if args.list_windows:
        titles = _list_window_titles()
        print(f"windows.count {len(titles)}")
        # Keep output readable; still print everything (usually small).
        for t in titles:
            print(" -", t)

    cfg = _load_enabled_profile_config(REPO_ROOT / "file.json")
    raw_ng_runtime = cfg.get("ng_runtime")
    ng_runtime: Dict[str, Any] = dict(raw_ng_runtime) if isinstance(raw_ng_runtime, dict) else {}

    ctx: Dict[str, Any] = {"ng_runtime": dict(ng_runtime)}
    ctx = setTibiaWindowMiddleware(ctx)

    if not args.no_screenshot:
        # Populates ng_capture_rect/ng_action_rect and validates capture pipeline.
        ctx = setScreenshotMiddleware(ctx)

        # Optional UI sanity checks: if these are not visible in the capture,
        # the bot will be unable to navigate/attack/loot reliably.
        screenshot = ctx.get("ng_screenshot")
        if screenshot is not None:
            try:
                from src.repositories.radar.locators import getRadarToolsPosition
                from src.repositories.radar.core import getCoordinate
                from src.repositories.battleList.locators import getBattleListIconPosition
                from src.repositories.battleList.extractors import getContent as getBattleListContent
                from src.repositories.chat.core import getChatMessagesContainerPosition, getTabs as getChatTabs

                radar_tools = getRadarToolsPosition(screenshot)
                radar_dbg: Dict[str, Any] = {}
                radar_coord = getCoordinate(screenshot, previousCoordinate=None, debug=radar_dbg)
                battle_icon = getBattleListIconPosition(screenshot)
                battle_content = getBattleListContent(screenshot)
                chat_tabs = getChatTabs(screenshot)
                chat_msgs = getChatMessagesContainerPosition(screenshot)

                print("ui.radar_tools_found", radar_tools is not None)
                print("ui.radar_coord", radar_coord)
                if radar_coord is None:
                    # Keep this compact; detailed dumps are handled by the runtime middleware.
                    print("ui.radar_coord_dbg", {k: radar_dbg.get(k) for k in ("radar_tools", "floor_level", "radar_phase_resp") if k in radar_dbg})
                    # Preflight-only dump: helps debugging coord issues without launching the bot.
                    if radar_tools is not None:
                        try:
                            import time
                            import cv2
                            from src.repositories.radar.extractors import getRadarImage
                            from src.repositories.radar.core import getFloorLevel

                            out_dir = REPO_ROOT / 'debug'
                            out_dir.mkdir(parents=True, exist_ok=True)
                            ts = int(time.time())
                            radar_crop = getRadarImage(screenshot, radar_tools)
                            cv2.imwrite(str(out_dir / f'preflight_radar_match_not_found_{ts}_radar.png'), radar_crop)
                            floor_level = getFloorLevel(screenshot)
                            meta = {
                                'timestamp': ts,
                                'tools_pos': list(map(int, radar_tools)),
                                'floor_level': int(floor_level) if floor_level is not None else None,
                                'radar_shape': list(map(int, getattr(radar_crop, 'shape', (0, 0)))),
                            }
                            (out_dir / f'preflight_radar_match_not_found_{ts}.json').write_text(
                                json.dumps(meta, indent=2), encoding='utf-8'
                            )
                            print(f"preflight.dumped_radar {out_dir / f'preflight_radar_match_not_found_{ts}_radar.png'}")
                        except Exception:
                            pass
                print("ui.battlelist_icon_found", battle_icon is not None)
                print("ui.battlelist_content_found", battle_content is not None)
                print("ui.chat_tabs", sorted(list(chat_tabs.keys())) if isinstance(chat_tabs, dict) else [])
                print("ui.chat_messages_found", chat_msgs is not None)

                warnings: list[str] = []
                if radar_tools is None:
                    warnings.append(
                        "Radar tools not found in capture (coord will be None). Ensure minimap + its tools are visible in the capture and not covered."
                    )
                if battle_content is None:
                    warnings.append(
                        "Battle list not found in capture (bot won't see creatures). Ensure the Battle List panel is open/visible in the capture (not minimized/hidden)."
                    )
                if not (isinstance(chat_tabs, dict) and "loot" in chat_tabs):
                    warnings.append(
                        "Loot chat tab not detected in capture (loot trigger may never fire). Ensure a 'Loot' tab exists and is visible in the capture."
                    )
                if chat_msgs is None:
                    warnings.append(
                        "Chat messages container not found in capture (loot parsing will fail). Ensure the chat panel is visible and matches the expected UI (try classic size/position; avoid heavy scaling)."
                    )

                if warnings:
                    print("WARN: UI preflight found potential issues:")
                    for w in warnings:
                        print(" -", w)
            except Exception:
                # Preflight must never fail due to optional UI checks.
                pass

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
