from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate, getFloorLevel
from src.repositories.radar.locators import getRadarToolsPosition
from src.repositories.gameWindow.core import getLeftArrowPosition, getRightArrowPosition
from src.gameplay.typings import Context

import cv2
import os
import pathlib
import time


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
    context['ng_radar']['coordinate'] = coordinate

    if coordinate is not None:
        context['ng_radar']['previousCoordinate'] = coordinate
        diag['consecutive_radar_tools_missing'] = 0
        diag['consecutive_game_window_arrows_missing'] = 0
        if context.get('ng_debug') is not None:
            context['ng_debug']['radar_tools'] = True
            context['ng_debug']['floor_level'] = coordinate[2]
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

    # Dump frames when we keep failing to see radar/arrows to avoid silent stalls.
    radar_thr = int(os.getenv('FENRIL_DIAG_RADAR_MISSING_THRESHOLD', '30'))
    arrows_thr = int(os.getenv('FENRIL_DIAG_ARROWS_MISSING_THRESHOLD', '30'))
    should_dump = (
        int(diag.get('consecutive_radar_tools_missing', 0)) >= radar_thr
        or int(diag.get('consecutive_game_window_arrows_missing', 0)) >= arrows_thr
    )
    if should_dump:
        now = time.time()
        last_dump = float(diag.get('last_radar_dump_time', 0.0))
        if now - last_dump >= 5.0:
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
