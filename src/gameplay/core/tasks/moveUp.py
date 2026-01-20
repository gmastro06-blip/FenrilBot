from src.utils.keyboard import press
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.utils.core import getScreenshot, getScreenshotDebugInfo, setScreenshotOutputIdx
from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate
from src.gameplay.core.waypoint import resolveGoalCoordinate

class MoveUp(BaseTask):
    def __init__(self, context: Context, direction: str) -> None:
        super().__init__()
        self.name = 'moveUp'
        self.isRootTask = True
        self.direction = direction
        self.floorLevel = context['ng_radar']['coordinate'][2] - 1

    # TODO: add unit tests
    # TODO: improve this code
    def do(self, context: Context) -> Context:
        direction_map = {
            'north': 'up',
            'south': 'down',
            'west': 'left',
            'east': 'right',
        }
        direction = direction_map.get(self.direction)
        if direction is None:
            return context
        press(direction)
        return context

    # TODO: add unit tests
    def onComplete(self, context: Context) -> Context:
        # Refresh screenshot from the capture window (OBS projector) region.
        try:
            out_idx = context.get('ng_capture_output_idx')
            if out_idx is not None and getScreenshotDebugInfo().get('output_idx') != out_idx:
                setScreenshotOutputIdx(int(out_idx))
        except Exception:
            pass
        context['ng_screenshot'] = getScreenshot(
            region=context.get('ng_capture_region'),
            absolute_region=context.get('ng_capture_absolute_region'),
        )
        context['ng_radar']['coordinate'] = getCoordinate(
            context['ng_screenshot'], previousCoordinate=context['ng_radar']['previousCoordinate'])
        if context['ng_radar']['coordinate'][2] != self.floorLevel:
            context['ng_cave']['waypoints']['currentIndex'] = getClosestWaypointIndexFromCoordinate(
                context['ng_radar']['coordinate'], context['ng_cave']['waypoints']['items'])
            currentWaypoint = context['ng_cave']['waypoints']['items'][context['ng_cave']
                                                                ['waypoints']['currentIndex']]
            context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(
                context['ng_radar']['coordinate'], currentWaypoint)
        return context
