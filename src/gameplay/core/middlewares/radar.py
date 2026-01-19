from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate
from ...typings import Context


# TODO: add unit tests
def setRadarMiddleware(context: Context) -> Context:
    if context['ng_screenshot'] is None:
        context['ng_radar']['coordinate'] = None
        return context
    context['ng_radar']['coordinate'] = getCoordinate(
        context['ng_screenshot'], previousCoordinate=context['ng_radar']['previousCoordinate'])
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
        context['ng_cave']['waypoints']['currentIndex'] = getClosestWaypointIndexFromCoordinate(
            context['ng_radar']['coordinate'], context['ng_cave']['waypoints']['items'])
    return context
