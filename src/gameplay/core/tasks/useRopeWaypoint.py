from src.shared.typings import Waypoint
from src.gameplay.typings import Context
from .common.vector import VectorTask
from .useRope import UseRopeTask
from .setNextWaypoint import SetNextWaypointTask
from .walkToCoordinate import WalkToCoordinateTask
from src.utils.core import getScreenshot, getScreenshotDebugInfo, setScreenshotOutputIdx
from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate
from src.gameplay.core.waypoint import resolveGoalCoordinate

class UseRopeWaypointTask(VectorTask):
    def __init__(self: "UseRopeWaypointTask", waypoint: Waypoint) -> None:
        super().__init__()
        self.name = 'useRopeWaypoint'
        self.isRootTask = True
        self.waypoint = waypoint
        self.failedAttempts = 0  # Track failed rope attempts

    def onBeforeStart(self, context: Context) -> Context:
        self.tasks = [
            WalkToCoordinateTask(self.waypoint['coordinate']).setParentTask(self).setRootTask(self),
            UseRopeTask(self.waypoint).setParentTask(self).setRootTask(self),
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
        context['ng_radar']['coordinate'] = getCoordinate(
            context['ng_screenshot'], previousCoordinate=context['ng_radar']['previousCoordinate'])
        coord = context['ng_radar']['coordinate']
        if coord is None:
            return context
        
        # Persistent failure tracking key for this specific waypoint
        waypoint_key = f'rope_fails_{self.waypoint["coordinate"][0]}_{self.waypoint["coordinate"][1]}_{self.waypoint["coordinate"][2]}'
        
        expected_z = self.waypoint['coordinate'][2] - 1
        if context['ng_radar']['coordinate'][2] != expected_z:
            # Rope failed - increment persistent counter
            current_fails = context.get(waypoint_key, 0) + 1
            context[waypoint_key] = current_fails
            
            if current_fails >= 3:
                # After 3 failures, force skip to next waypoint
                print(f'[UseRopeWaypoint] FAILED {current_fails} times at {self.waypoint["coordinate"]}, expected Z={expected_z}. Auto-skipping.')
                # Advance manually since rope failed
                context['ng_cave']['waypoints']['currentIndex'] = min(
                    context['ng_cave']['waypoints']['currentIndex'] + 1,
                    len(context['ng_cave']['waypoints']['items']) - 1
                )
                # Clean up counter after skip
                del context[waypoint_key]
            else:
                # Still trying - reset to closest waypoint
                context['ng_cave']['waypoints']['currentIndex'] = getClosestWaypointIndexFromCoordinate(
                    context['ng_radar']['coordinate'], context['ng_cave']['waypoints']['items'])
            currentWaypoint = context['ng_cave']['waypoints']['items'][context['ng_cave']
                                                                ['waypoints']['currentIndex']]
            context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(
                context['ng_radar']['coordinate'], currentWaypoint)
        else:
            # Success - clean up counter
            if waypoint_key in context:
                del context[waypoint_key]
        return context
