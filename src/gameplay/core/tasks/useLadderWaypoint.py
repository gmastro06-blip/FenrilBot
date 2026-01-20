from src.shared.typings import Waypoint
from src.gameplay.typings import Context
from .common.vector import VectorTask
from .rightClickUse import RightClickUseTask
from .setNextWaypoint import SetNextWaypointTask
from src.utils.core import getScreenshot, getScreenshotDebugInfo, setScreenshotOutputIdx
from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate
from src.gameplay.core.waypoint import resolveGoalCoordinate

class UseLadderWaypointTask(VectorTask):
    def __init__(self: "UseLadderWaypointTask", waypoint: Waypoint) -> None:
        super().__init__()
        self.name = 'useLadderWaypoint'
        self.isRootTask = True
        self.waypoint = waypoint

    def onBeforeStart(self, context: Context) -> Context:
        self.tasks = [
            RightClickUseTask(self.waypoint).setParentTask(self).setRootTask(self),
            SetNextWaypointTask().setParentTask(self).setRootTask(self),  # type: ignore
        ]
        return context

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
        try:
            coord = getCoordinate(
                context['ng_screenshot'], previousCoordinate=context['ng_radar']['previousCoordinate'])
        except Exception:
            coord = None
        context['ng_radar']['coordinate'] = coord

        if coord is None:
            return context

        if coord[2] != self.waypoint['coordinate'][2] - 1:
            context['ng_cave']['waypoints']['currentIndex'] = getClosestWaypointIndexFromCoordinate(
                coord, context['ng_cave']['waypoints']['items'])
            currentWaypoint = context['ng_cave']['waypoints']['items'][context['ng_cave']
                                                                ['waypoints']['currentIndex']]
            context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(
                coord, currentWaypoint)
        return context
