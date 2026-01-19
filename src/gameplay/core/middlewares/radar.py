from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate, getFloorLevel
from src.repositories.radar.locators import getRadarToolsPosition
from src.gameplay.typings import Context


# TODO: add unit tests
def setRadarMiddleware(context: Context) -> Context:
    if context['ng_screenshot'] is None:
        context['ng_radar']['coordinate'] = None
        if context.get('ng_debug') is not None:
            context['ng_debug']['radar_tools'] = None
            context['ng_debug']['floor_level'] = None
        return context

    coordinate = getCoordinate(
        context['ng_screenshot'], previousCoordinate=context['ng_radar']['previousCoordinate'])
    context['ng_radar']['coordinate'] = coordinate

    if coordinate is not None:
        context['ng_radar']['previousCoordinate'] = coordinate
        if context.get('ng_debug') is not None:
            context['ng_debug']['radar_tools'] = True
            context['ng_debug']['floor_level'] = coordinate[2]
        return context

    # Diagnostics: why did getCoordinate return None?
    if context.get('ng_debug') is not None:
        tools_pos = getRadarToolsPosition(context['ng_screenshot'])
        context['ng_debug']['radar_tools'] = tools_pos is not None
        if tools_pos is None:
            context['ng_debug']['last_tick_reason'] = 'radar tools not found'
            context['ng_debug']['floor_level'] = None
        else:
            floor_level = getFloorLevel(context['ng_screenshot'])
            context['ng_debug']['floor_level'] = floor_level
            if floor_level is None:
                context['ng_debug']['last_tick_reason'] = 'floor level not found'
            else:
                context['ng_debug']['last_tick_reason'] = 'radar match not found'
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
