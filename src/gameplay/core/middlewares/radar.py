from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate, getFloorLevel
from src.repositories.radar.extractors import getRadarImage
from src.repositories.radar.config import images as radarImages
from src.repositories.radar.config import dimensions as radarDimensions
from src.repositories.radar.locators import getRadarToolsPosition
from src.repositories.gameWindow.core import getLeftArrowPosition, getRightArrowPosition
from src.repositories.gameWindow.config import gameWindowCache
from src.gameplay.typings import Context

import cv2
import json
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
    prev_radar_img = context.get('ng_radar', {}).get('previousRadarImage')
    coordinate = getCoordinate(
        context['ng_screenshot'], context['ng_radar']['previousCoordinate'], debug, previousRadarImage=prev_radar_img)

    # If we don't have a previousCoordinate yet, require a short stability window
    # before trusting a potentially low-confidence full-floor match.
    if coordinate is not None and context.get('ng_radar', {}).get('previousCoordinate') is None:
        try:
            pending = context['ng_radar'].get('pendingCoordinate')
            ticks = int(context['ng_radar'].get('pendingCoordinateTicks', 0))
            required = get_int(
                context,
                'ng_runtime.radar_lock_on_confirm_ticks',
                env_var='FENRIL_RADAR_LOCK_ON_CONFIRM_TICKS',
                default=2,
            )
            required = max(2, int(required))
            same = False
            if isinstance(pending, (tuple, list)) and len(pending) == 3:
                same = (pending[2] == coordinate[2] and abs(int(pending[0]) - int(coordinate[0])) <= 1 and abs(int(pending[1]) - int(coordinate[1])) <= 1)
            if same:
                ticks += 1
            else:
                pending = coordinate
                ticks = 1
            context['ng_radar']['pendingCoordinate'] = pending
            context['ng_radar']['pendingCoordinateTicks'] = ticks
            if ticks < int(required):
                # Hold off one tick to reduce false positives.
                coordinate = None
                context['ng_radar']['lockConfirmed'] = False
                if debug is not None:
                    debug['last_tick_reason'] = 'radar lock-on pending'
            else:
                coordinate = tuple(pending)  # type: ignore[assignment]
                context['ng_radar']['pendingCoordinate'] = None
                context['ng_radar']['pendingCoordinateTicks'] = 0
                context['ng_radar']['lockConfirmed'] = True
        except Exception:
            pass

    # Reject implausible coordinate jumps (usually false-positive match on full-floor).
    try:
        prev_coord = context.get('ng_radar', {}).get('previousCoordinate')
        lock_ok = bool(context.get('ng_radar', {}).get('lockConfirmed'))
        if (
            coordinate is not None
            and prev_coord is not None
            and isinstance(prev_coord, (tuple, list))
            and len(prev_coord) == 3
            and prev_coord[2] == coordinate[2]
            and lock_ok
        ):
            max_jump = get_int(
                context,
                'ng_runtime.radar_max_jump',
                env_var='FENRIL_RADAR_MAX_JUMP',
                default=12,
            )
            dx = abs(int(coordinate[0]) - int(prev_coord[0]))
            dy = abs(int(coordinate[1]) - int(prev_coord[1]))
            if dx > int(max_jump) or dy > int(max_jump):
                coordinate = None
                if debug is not None:
                    debug['last_tick_reason'] = 'radar jump rejected'
    except Exception:
        pass

    # Store current radar crop for next tick tracking.
    try:
        tools_now = getRadarToolsPosition(context['ng_screenshot'])
        if tools_now is not None:
            radar_now = getRadarImage(context['ng_screenshot'], tools_now)
            if getattr(radar_now, 'size', 0) != 0:
                context['ng_radar']['radarImage'] = radar_now
                context['ng_radar']['previousRadarImage'] = radar_now
    except Exception:
        pass

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

        # Optional: dump immediately when radar tools + floor level are present,
        # but minimap->floor matching fails (common with scaling/offset issues).
        if (
            floor_level is not None
            and get_bool(
                context,
                'ng_runtime.dump_radar_match_on_fail',
                env_var='FENRIL_DUMP_RADAR_MATCH_ON_FAIL',
                default=False,
            )
        ):
            now = time.time()
            min_interval = get_float(
                context,
                'ng_runtime.dump_radar_match_min_interval_s',
                env_var='FENRIL_DUMP_RADAR_MATCH_MIN_INTERVAL_S',
                default=60.0,
            )
            last_dump = float(diag.get('last_radar_match_dump_time', 0.0))
            if now - last_dump >= min_interval:
                diag['last_radar_match_dump_time'] = now
                out_dir = pathlib.Path('debug')
                out_dir.mkdir(parents=True, exist_ok=True)

                # Save canonical radar crop.
                try:
                    radar_crop = getRadarImage(screenshot, tools_pos)
                    cv2.imwrite(str(out_dir / f'dual_diag_radar_match_not_found_{int(now)}_radar.png'), radar_crop)
                except Exception:
                    radar_crop = None

                # Save a larger region around the minimap/tools for visual inspection.
                try:
                    left, top, found_w, found_h = tools_pos
                    img_h, img_w = screenshot.shape[:2]

                    # Infer scale for a reasonable padding.
                    try:
                        tpl_h, tpl_w = radarImages['tools'].shape[:2]
                        scale_x = float(found_w) / float(tpl_w) if tpl_w else 1.0
                        scale_y = float(found_h) / float(tpl_h) if tpl_h else 1.0
                        scale = (scale_x + scale_y) / 2.0
                        if scale <= 0:
                            scale = 1.0
                    except Exception:
                        scale = 1.0

                    # Ensure we capture the full minimap area, which extends ~radarWidth
                    # pixels to the LEFT of the tools icon.
                    pad_x_left = int(round((int(radarDimensions.get('width', 106)) + 60) * scale))
                    pad_x_right = int(round(80 * scale))
                    pad_y = int(round(80 * scale))

                    x0 = max(0, int(left) - pad_x_left)
                    y0 = max(0, int(top) - pad_y)
                    x1 = min(img_w, int(left + found_w + pad_x_right))
                    y1 = min(img_h, int(top + found_h + pad_y))
                    ui_crop = screenshot[y0:y1, x0:x1]
                    if ui_crop.size:
                        cv2.imwrite(str(out_dir / f'dual_diag_radar_match_not_found_{int(now)}_ui.png'), ui_crop)

                    # Save the floor-level strip crop (normalized).
                    fx0 = int(left + found_w + int(round(8 * scale)))
                    fy0 = int(top - int(round(7 * scale)))
                    fw = max(1, int(round(2 * scale)))
                    fh = max(1, int(round(67 * scale)))
                    fx1 = min(img_w, fx0 + fw)
                    fy1 = min(img_h, fy0 + fh)
                    fx0 = max(0, fx0)
                    fy0 = max(0, fy0)
                    floor_strip = screenshot[fy0:fy1, fx0:fx1]
                    if floor_strip.size:
                        try:
                            floor_strip_norm = cv2.resize(floor_strip, (2, 67), interpolation=cv2.INTER_AREA if scale > 1.0 else cv2.INTER_LINEAR)
                        except Exception:
                            floor_strip_norm = floor_strip
                        cv2.imwrite(str(out_dir / f'dual_diag_radar_match_not_found_{int(now)}_floorstrip.png'), floor_strip_norm)

                    # Metadata for matching issues.
                    meta = {
                        'timestamp': now,
                        'tools_pos': list(map(int, tools_pos)),
                        'scale_estimate': float(scale),
                        'floor_level': int(floor_level),
                        'ui_crop_bbox': [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                        'floor_strip_bbox_raw': [int(fx0), int(fy0), int(fx1 - fx0), int(fy1 - fy0)],
                    }
                    (out_dir / f'dual_diag_radar_match_not_found_{int(now)}.json').write_text(
                        json.dumps(meta, indent=2), encoding='utf-8'
                    )
                    print(f"[fenril][dual] Diagnostics: radar match not found - dumped dual_diag_radar_match_not_found_{int(now)}_* to {out_dir}")
                except Exception:
                    pass

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
