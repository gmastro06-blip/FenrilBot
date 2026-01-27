from __future__ import annotations

import json
import pathlib
import sys
import time
from typing import Any, Dict

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.esc_stop import install_esc_stop

# Allow aborting long diagnostics with ESC.
install_esc_stop(exit_process=True)

from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware
from src.gameplay.core.middlewares.radar import setRadarMiddleware


def _load_enabled_profile_config(file_path: pathlib.Path) -> Dict[str, Any]:
    data = json.loads(file_path.read_text(encoding="utf-8"))
    default_table = data.get("_default") if isinstance(data, dict) else None
    if not isinstance(default_table, dict):
        return {}
    for _, row in default_table.items():
        if not isinstance(row, dict):
            continue
        cfg = row.get("config")
        if row.get("enabled") is True and isinstance(cfg, dict):
            return dict(cfg)
    for _, row in default_table.items():
        if not isinstance(row, dict):
            continue
        cfg = row.get("config")
        if isinstance(cfg, dict):
            return dict(cfg)
    return {}


def main() -> int:
    cfg = _load_enabled_profile_config(REPO_ROOT / 'file.json')
    ng_runtime = dict(cfg.get('ng_runtime') or {})

    ctx: Dict[str, Any] = {
        'ng_runtime': ng_runtime,
        'ng_debug': {'last_tick_reason': None, 'last_exception': None},
        'ng_diag': {},
        'ng_radar': {
            'coordinate': None,
            'previousCoordinate': None,
            'lastCoordinateVisited': None,
            'radarImage': None,
            'previousRadarImage': None,
            'pendingCoordinate': None,
            'pendingCoordinateTicks': 0,
            'lockConfirmed': False,
        },
    }

    ctx = setTibiaWindowMiddleware(ctx)

    n = int(ng_runtime.get('diag_radar_frames') or 20)
    sleep_s = float(ng_runtime.get('diag_radar_interval_s') or 0.25)

    print('frames', n, 'interval_s', sleep_s)

    for i in range(n):
        ctx = setScreenshotMiddleware(ctx)
        ctx = setRadarMiddleware(ctx)
        radar = ctx.get('ng_radar', {}) if isinstance(ctx.get('ng_radar'), dict) else {}
        coord = radar.get('coordinate')
        prev = radar.get('previousCoordinate')
        pend_ticks = radar.get('pendingCoordinateTicks')
        lock_ok = radar.get('lockConfirmed')
        lock_age = radar.get('lockAgeTicks')
        dbg = ctx.get('ng_debug', {}) if isinstance(ctx.get('ng_debug'), dict) else {}
        reason = dbg.get('last_tick_reason')
        cand = dbg.get('radar_candidate_coordinate')
        jump = dbg.get('radar_jump_dxdy')
        diag = ctx.get('ng_diag', {}) if isinstance(ctx.get('ng_diag'), dict) else {}
        miss = diag.get('consecutive_radar_coord_missing')
        print(f"{i:02d} coord={coord} prev={prev} pend_ticks={pend_ticks} lock={lock_ok} age={lock_age} reason={reason} miss={miss} cand={cand} jump={jump}")
        time.sleep(sleep_s)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
