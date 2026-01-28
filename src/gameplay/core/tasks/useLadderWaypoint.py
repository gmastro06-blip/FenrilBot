from src.shared.typings import Waypoint
from src.gameplay.typings import Context
from .common.vector import VectorTask
from .rightClickUse import RightClickUseTask
from .setNextWaypoint import SetNextWaypointTask
from .walkToCoordinate import WalkToCoordinateTask
from src.utils.core import getScreenshot, getScreenshotDebugInfo, setScreenshotOutputIdx
from src.repositories.radar.core import getClosestWaypointIndexFromCoordinate, getCoordinate
from src.gameplay.core.waypoint import resolveGoalCoordinate

class UseLadderWaypointTask(VectorTask):
    def __init__(self: "UseLadderWaypointTask", waypoint: Waypoint) -> None:
        super().__init__()
        self.name = 'useLadderWaypoint'
        self.isRootTask = True
        self.waypoint = waypoint
        self.failedAttempts = 0  # Track failed ladder attempts

    def onBeforeStart(self, context: Context) -> Context:
        self.tasks = [
            WalkToCoordinateTask(self.waypoint['coordinate']).setParentTask(self).setRootTask(self),
            RightClickUseTask(self.waypoint, expectedZ=self.waypoint['coordinate'][2] - 1).setParentTask(self).setRootTask(self),
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
        
        # CRÍTICO: Dar tiempo al radar a actualizarse después del cambio de piso
        from time import sleep
        sleep(0.3)
        
        try:
            coord = getCoordinate(
                context['ng_screenshot'], previousCoordinate=context['ng_radar']['previousCoordinate'])
        except Exception:
            coord = None
        context['ng_radar']['coordinate'] = coord

        if coord is None:
            return context

        # Persistent failure tracking key for this specific waypoint
        waypoint_key = f'ladder_fails_{self.waypoint["coordinate"][0]}_{self.waypoint["coordinate"][1]}_{self.waypoint["coordinate"][2]}'
        
        # CRÍTICO: Lógica corregida - avanzar waypoint SOLO si el cambio de piso fue exitoso
        expected_z = self.waypoint['coordinate'][2] - 1
        if coord[2] == expected_z:
            # Éxito: avanzar al siguiente waypoint
            from src.utils.array import getNextArrayIndex
            next_idx = getNextArrayIndex(
                context['ng_cave']['waypoints']['items'],
                context['ng_cave']['waypoints']['currentIndex']
            )
            context['ng_cave']['waypoints']['currentIndex'] = next_idx
            current_wp = context['ng_cave']['waypoints']['items'][next_idx]
            context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(coord, current_wp)
            # Reset failure counter on success
            if waypoint_key in context:
                del context[waypoint_key]
        else:
            # Fallo: incrementar contador persistente
            current_fails = context.get(waypoint_key, 0) + 1
            context[waypoint_key] = current_fails
            
            if current_fails >= 3:
                # After 3 failures, force skip to next waypoint
                print(f'[UseLadderWaypoint] FAILED {current_fails} times at {self.waypoint["coordinate"]}, expected Z={expected_z}. Auto-skipping.')
                # Advance manually since ladder failed
                from src.utils.array import getNextArrayIndex
                next_idx = getNextArrayIndex(
                    context['ng_cave']['waypoints']['items'],
                    context['ng_cave']['waypoints']['currentIndex']
                )
                context['ng_cave']['waypoints']['currentIndex'] = next_idx
                current_wp = context['ng_cave']['waypoints']['items'][next_idx]
                context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(coord, current_wp)
                # Clean up counter after skip
                del context[waypoint_key]
            else:
                # Reposicionar al waypoint más cercano para reintentar
                context['ng_cave']['waypoints']['currentIndex'] = getClosestWaypointIndexFromCoordinate(
                    coord, context['ng_cave']['waypoints']['items'])
                currentWaypoint = context['ng_cave']['waypoints']['items'][context['ng_cave']
                                                                    ['waypoints']['currentIndex']]
                context['ng_cave']['waypoints']['state'] = resolveGoalCoordinate(
                    coord, currentWaypoint)
        return context
