from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate, getFloorLevel
from src.repositories.radar.locators import getRadarToolsPosition
from src.repositories.gameWindow.core import getLeftArrowPosition, getRightArrowPosition
from src.repositories.gameWindow.config import gameWindowCache
from src.gameplay.typings import Context

import cv2
import os
import pathlib
import time

from src.utils.runtime_settings import get_bool, get_float, get_int


# TODO: add unit tests
def setRadarMiddleware(context: Context) -> Context:
    diag = context.get('ng_diag') if isinstance(context.get('ng_diag'), dict) else None
    if diag is None:
        diag = {}
        context['ng_diag'] = diag

    if context['ng_screenshot'] is None:
        context['ng_radar']['coordinate'] = None
        diag['consecutive_radar_tools_missing'] = 0
        diag['consecutive_game_window_arrows_missing'] = 0
        if context.get('ng_debug') is not None:
            context['ng_debug']['radar_tools'] = None
            context['ng_debug']['floor_level'] = None
        return context

    debug = context.get('ng_debug') if isinstance(context.get('ng_debug'), dict) else None
    coordinate = getCoordinate(
        context['ng_screenshot'], context['ng_radar']['previousCoordinate'], debug)

    # When template matching is flaky (OBS scaling / transient frame glitches),
    # allow a short-lived fallback to the last good coordinate to avoid hard stalls.
    if coordinate is None:
        diag['consecutive_radar_coord_missing'] = int(diag.get('consecutive_radar_coord_missing', 0)) + 1
        use_prev = get_bool(
            context,
            'ng_runtime.radar_use_previous_on_miss',
            env_var='FENRIL_RADAR_USE_PREVIOUS_ON_MISS',
            default=True,
        )
        max_prev_ticks = get_int(
            context,
            'ng_runtime.radar_use_previous_max_ticks',
            env_var='FENRIL_RADAR_USE_PREVIOUS_MAX_TICKS',
            default=3,
        )
        prev_coord = context.get('ng_radar', {}).get('previousCoordinate')
        if use_prev and prev_coord is not None and int(diag.get('consecutive_radar_coord_missing', 0)) <= max_prev_ticks:
            coordinate = prev_coord
            diag['radar_used_previous_on_miss'] = int(diag.get('radar_used_previous_on_miss', 0)) + 1
            if debug is not None and debug.get('last_tick_reason') in (None, 'running', 'no coord'):
                debug['last_tick_reason'] = 'radar miss (using previous)'
    else:
        diag['consecutive_radar_coord_missing'] = 0

    context['ng_radar']['coordinate'] = coordinate

    if coordinate is not None:
        context['ng_radar']['previousCoordinate'] = coordinate
        diag['consecutive_radar_tools_missing'] = 0
        diag['consecutive_game_window_arrows_missing'] = 0
        if context.get('ng_debug') is not None:
            context['ng_debug']['radar_tools'] = True
            context['ng_debug']['floor_level'] = coordinate[2]
            # Clear stale failure reasons so the pilot loop can report "running".
            if context['ng_debug'].get('last_tick_reason') in (
                'radar tools not found',
                'floor level not found',
                'radar match not found',
            ):
                context['ng_debug']['last_tick_reason'] = None
        return context

    # Diagnostics: why did getCoordinate return None?
    screenshot = context['ng_screenshot']
    tools_pos = getRadarToolsPosition(screenshot)
    left_arrow = getLeftArrowPosition(screenshot)
    right_arrow = getRightArrowPosition(screenshot)

    debug = context.get('ng_debug') if isinstance(context.get('ng_debug'), dict) else None
    if debug is not None:
        debug['radar_tools'] = tools_pos is not None
        debug['game_window_left_arrow'] = left_arrow
        debug['game_window_right_arrow'] = right_arrow

    if tools_pos is None:
        diag['consecutive_radar_tools_missing'] = int(diag.get('consecutive_radar_tools_missing', 0)) + 1
        if debug is not None:
            debug['last_tick_reason'] = 'radar tools not found'
            debug['floor_level'] = None

        # Optional: dump immediately on radar-tools miss (useful for short test runs).
        if get_bool(context, 'ng_runtime.dump_radar_on_fail', env_var='FENRIL_DUMP_RADAR_ON_FAIL', default=False):
            now = time.time()
            min_interval = get_float(
                context,
                'ng_runtime.dump_radar_min_interval_s',
                env_var='FENRIL_DUMP_RADAR_MIN_INTERVAL_S',
                default=60.0,
            )
            last_dump = float(diag.get('last_radar_dump_time', 0.0))
            if now - last_dump >= min_interval:
                diag['last_radar_dump_time'] = now
                out_dir = pathlib.Path('debug')
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / f'dual_diag_radar_tools_missing_{int(now)}.png'
                try:
                    cv2.imwrite(str(path), screenshot)
                    print(f"[fenril][dual] Diagnostics: radar tools not found - dumped {path}")
                except Exception:
                    pass

        # Recovery: reset locator caches after repeated misses.
        reset_thr = get_int(
            context,
            'ng_runtime.reset_locator_cache_threshold',
            env_var='FENRIL_RESET_LOCATOR_CACHE_THRESHOLD',
            default=10,
        )
        if int(diag.get('consecutive_radar_tools_missing', 0)) >= reset_thr:
            try:
                reset_fn = getattr(getRadarToolsPosition, 'reset_cache', None)
                if callable(reset_fn):
                    reset_fn()
            except Exception:
                pass
    else:
        diag['consecutive_radar_tools_missing'] = 0
        floor_level = getFloorLevel(screenshot)
        if debug is not None:
            debug['floor_level'] = floor_level
            if floor_level is None:
                debug['last_tick_reason'] = 'floor level not found'
            else:
                debug['last_tick_reason'] = 'radar match not found'

    arrows_ok = left_arrow is not None and right_arrow is not None
    if not arrows_ok:
        diag['consecutive_game_window_arrows_missing'] = int(diag.get('consecutive_game_window_arrows_missing', 0)) + 1
    else:
        diag['consecutive_game_window_arrows_missing'] = 0

    # Recovery: clear the game-window arrow cache after repeated misses.
    reset_thr = get_int(
        context,
        'ng_runtime.reset_locator_cache_threshold',
        env_var='FENRIL_RESET_LOCATOR_CACHE_THRESHOLD',
        default=10,
    )
    if int(diag.get('consecutive_game_window_arrows_missing', 0)) >= reset_thr:
        try:
            gameWindowCache['left']['position'] = None
            gameWindowCache['left']['arrow'] = None
            gameWindowCache['right']['position'] = None
            gameWindowCache['right']['arrow'] = None
        except Exception:
            pass

    # Dump frames when we keep failing to see radar/arrows.
    # This is helpful during setup but can spam `debug/` in long runs.
    # Default is OFF; enable with FENRIL_DUMP_RADAR_PERSISTENT=1.
    radar_thr = get_int(
        context,
        'ng_runtime.diag_radar_missing_threshold',
        env_var='FENRIL_DIAG_RADAR_MISSING_THRESHOLD',
        default=30,
    )
    arrows_thr = get_int(
        context,
        'ng_runtime.diag_arrows_missing_threshold',
        env_var='FENRIL_DIAG_ARROWS_MISSING_THRESHOLD',
        default=30,
    )
    should_dump = (
        int(diag.get('consecutive_radar_tools_missing', 0)) >= radar_thr
        or int(diag.get('consecutive_game_window_arrows_missing', 0)) >= arrows_thr
    )
    if should_dump and get_bool(
        context,
        'ng_runtime.dump_radar_persistent',
        env_var='FENRIL_DUMP_RADAR_PERSISTENT',
        default=False,
    ):
        now = time.time()
        last_dump = float(diag.get('last_radar_dump_time', 0.0))
        min_interval = get_float(
            context,
            'ng_runtime.dump_radar_persistent_min_interval_s',
            env_var='FENRIL_DUMP_RADAR_PERSISTENT_MIN_INTERVAL_S',
            default=120.0,
        )
        if now - last_dump >= min_interval:
            diag['last_radar_dump_time'] = now
            out_dir = pathlib.Path('debug')
            out_dir.mkdir(parents=True, exist_ok=True)
            reason = 'radar_tools_missing' if tools_pos is None else 'arrows_missing'
            path = out_dir / f'dual_diag_{reason}_{int(now)}.png'
            try:
                cv2.imwrite(str(path), screenshot)
                print(
                    f"[fenril][dual] Diagnostics: {reason} (radar_missing={diag.get('consecutive_radar_tools_missing')} arrows_missing={diag.get('consecutive_game_window_arrows_missing')}) - dumped {path}"
                )
            except Exception:
                pass
    return context


# TODO: add unit tests
def setWaypointIndexMiddleware(context: Context) -> Context:
    if context['ng_cave']['waypoints']['currentIndex'] is None:
        if context['ng_radar']['coordinate'] is None:
            return context
        if any(coord is None for coord in context['ng_radar']['coordinate']):
            return context
        if not context['ng_cave']['waypoints']['items']:
            return context
        closest_index = getClosestWaypointIndexFromCoordinate(
            context['ng_radar']['coordinate'], context['ng_cave']['waypoints']['items'])
        context['ng_cave']['waypoints']['currentIndex'] = 0 if closest_index is None else closest_index
    return context
