import src.gameplay.utils as gameplayUtils
from src.shared.typings import Coordinate
from src.gameplay.typings import Context
from ..waypoint import generateFloorWalkpoints
from .common.vector import VectorTask
from .walk import WalkTask
from .attackMonstersBox import AttackMonstersBoxTask
from .lootMonstersBox import LootMonstersBoxTask
from .resetSpellIndex import ResetSpellIndexTask
from .clickInClosestCreature import ClickInClosestCreatureTask
from .walkToTargetCreature import WalkToTargetCreatureTask

class WalkToCoordinateTask(VectorTask):
    def __init__(self: "WalkToCoordinateTask", coordinate: Coordinate, passinho: bool = False) -> None:
        super().__init__()
        self.name = 'walkToCoordinate'
        self.coordinate = coordinate
        self.passinho = passinho
        self.isTrapped = False
        self.coordinateHistory = []  # Track last coordinates to detect loops
        self.stuckAttempts = 0  # Counter for failed reach attempts

    def shouldRestartAfterAllChildrensComplete(self, context: Context) -> bool:
        currentCoord = context['ng_radar']['coordinate']
        
        # Use persistent coordinate history in context
        history_key = f'walk_history_{self.coordinate[0]}_{self.coordinate[1]}_{self.coordinate[2]}'
        coord_history = context.get(history_key, [])
        
        # Detect coordinate oscillation loops
        coord_history.append(tuple(currentCoord))
        if len(coord_history) > 15:  # Keep last 15 coordinates
            coord_history.pop(0)
        context[history_key] = coord_history
        
        # FIX: Validar progreso hacia el objetivo (distancia decreciente)
        if len(coord_history) >= 5:
            import math
            # Calcular distancia actual al objetivo
            curr_dist = math.sqrt(
                (currentCoord[0] - self.coordinate[0])**2 + 
                (currentCoord[1] - self.coordinate[1])**2
            )
            
            # Calcular distancia hace 5 ticks
            old_coord = coord_history[-5]
            old_dist = math.sqrt(
                (old_coord[0] - self.coordinate[0])**2 + 
                (old_coord[1] - self.coordinate[1])**2
            )
            
            # Si NO estamos acercándonos (distancia no disminuye) y llevamos 5+ ticks
            if curr_dist >= old_dist - 1.0:  # Tolerance 1 sqm
                progress_key = f'walk_no_progress_{self.coordinate[0]}_{self.coordinate[1]}_{self.coordinate[2]}'
                no_progress_count = context.get(progress_key, 0) + 1
                context[progress_key] = no_progress_count
                
                if no_progress_count >= 3:  # 15 ticks sin progreso (3 grupos de 5)
                    print(f'[WalkToCoordinate] NO PROGRESS: Distance not decreasing ({old_dist:.1f} → {curr_dist:.1f} sqm). Recalculating path...')
                    context[progress_key] = 0  # Reset
                    # Force recalculation by clearing tasks
                    self.tasks = []
                    return True  # Restart to recalculate
            else:
                # Making progress, reset counter
                progress_key = f'walk_no_progress_{self.coordinate[0]}_{self.coordinate[1]}_{self.coordinate[2]}'
                if progress_key in context:
                    context[progress_key] = 0
        
        # Check if stuck (oscillating between same 2-3 coordinates OR staying in same spot)
        if len(coord_history) >= 10:
            uniqueCoords = list(set(coord_history[-10:]))
            if len(uniqueCoords) <= 3 and not gameplayUtils.coordinatesAreEqual(currentCoord, self.coordinate):
                # Stuck in loop - increment persistent counter
                stuck_key = f'walk_stuck_{self.coordinate[0]}_{self.coordinate[1]}_{self.coordinate[2]}'
                stuck_count = context.get(stuck_key, 0) + 1
                context[stuck_key] = stuck_count
                
                if stuck_count >= 3:
                    print(f'[WalkToCoordinate] STUCK IN LOOP: Oscillating between {uniqueCoords}, target unreachable at {self.coordinate}. Auto-skipping waypoint.')
                    # Clean up tracking
                    if history_key in context:
                        del context[history_key]
                    if stuck_key in context:
                        del context[stuck_key]
                    return False  # Don't restart, let task complete to advance waypoint
        
        # CRÍTICO: Si isTrapped, verificar si el camino ahora está libre antes de reiniciar
        if self.isTrapped == True:
            from src.utils.coordinate import is_valid_coordinate
            nonWalkableCoordinates = context['ng_cave']['holesOrStairs'].copy()
            for monster in context['gameWindow']['monsters']:
                coord = monster.get('coordinate')
                if is_valid_coordinate(coord):
                    nonWalkableCoordinates.append(coord)
            
            walkpoints = generateFloorWalkpoints(
                context['ng_radar']['coordinate'], 
                self.coordinate, 
                nonWalkableCoordinates=nonWalkableCoordinates
            )
            
            # Si ahora hay camino, desbloquear y reintentar walk
            if len(walkpoints) > 0:
                self.isTrapped = False
                return True
            # Si sigue bloqueado pero no hay monstruos, no reintentar (dejar que timeout)
            if len(context['gameWindow']['monsters']) == 0:
                return False
            # Si hay monstruos, continuar atacando
            return True
        if len(self.tasks) == 0:
            return True
        return not gameplayUtils.coordinatesAreEqual(context['ng_radar']['coordinate'], self.coordinate)

    def onBeforeStart(self, context: Context) -> Context:
        self.calculateWalkpoint(context)
        return context

    def onBeforeRestart(self, context: Context) -> Context:
        return self.onBeforeStart(context)

    def onInterrupt(self, context: Context) -> Context:
        return gameplayUtils.releaseKeys(context)

    def onComplete(self, context: Context) -> Context:
        return gameplayUtils.releaseKeys(context)

    # TODO: add unit tests
    def calculateWalkpoint(self, context: Context) -> None:
        from src.utils.coordinate import is_valid_coordinate
        nonWalkableCoordinates = context['ng_cave']['holesOrStairs'].copy()
        for monster in context['gameWindow']['monsters']:
            coord = monster.get('coordinate')
            if is_valid_coordinate(coord):
                nonWalkableCoordinates.append(coord)
        refillCheckerIndexPlayer = next((index for index, item in enumerate(context['ng_cave']['waypoints']['items']) if item['type'] == 'refillChecker'), None)
        if refillCheckerIndexPlayer is None or refillCheckerIndexPlayer is not None and context['ng_cave']['waypoints']['currentIndex'] < refillCheckerIndexPlayer:
            for player in context['gameWindow']['players']:
                coord = player.get('coordinate')
                if is_valid_coordinate(coord):
                    nonWalkableCoordinates.append(coord)
        self.tasks = []
        walkpoints = generateFloorWalkpoints(
                context['ng_radar']['coordinate'], self.coordinate, nonWalkableCoordinates=nonWalkableCoordinates)
        if len(walkpoints) == 0 and not gameplayUtils.coordinatesAreEqual(context['ng_radar']['coordinate'], self.coordinate):
            self.isTrapped = True
            if any(creature[0] != 'Unknown' for creature in context['ng_battleList']['creatures']):
                refillCheckerIndex = next((index for index, item in enumerate(context['ng_cave']['waypoints']['items']) if item['type'] == 'refillChecker'), None)
                if refillCheckerIndex is None or refillCheckerIndex is not None and context['ng_cave']['waypoints']['currentIndex'] < refillCheckerIndex:
                    self.tasks = [
                        AttackMonstersBoxTask().setParentTask(self).setRootTask(self),
                        LootMonstersBoxTask().setParentTask(self).setRootTask(self),
                        LootMonstersBoxTask().setParentTask(self).setRootTask(self),
                        LootMonstersBoxTask().setParentTask(self).setRootTask(self),
                        ResetSpellIndexTask().setParentTask(self).setRootTask(self),
                    ]
                else:
                    self.tasks = [
                        ClickInClosestCreatureTask().setParentTask(self).setRootTask(self.rootTask),
                        WalkToTargetCreatureTask().setParentTask(self).setRootTask(self.rootTask),
                    ]
        else:
            self.isTrapped = False
        for walkpoint in walkpoints:
            self.tasks.append(WalkTask(context, walkpoint, self.passinho).setParentTask(
                self).setRootTask(self.rootTask))
