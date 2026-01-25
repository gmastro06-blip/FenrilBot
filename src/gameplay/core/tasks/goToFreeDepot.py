import numpy as np
from typing import Any, Dict, Optional, cast

from src.repositories.battleList.typings import CreatureList
from src.shared.typings import Coordinate, CoordinateList, Waypoint
from src.wiki.cities import cities
from src.gameplay.typings import Context
from src.gameplay.core.waypoint import generateFloorWalkpoints
from .common.vector import VectorTask
from .walk import WalkTask

from src.utils.console_log import log

class GoToFreeDepotTask(VectorTask):
    def __init__(self, waypoint: Waypoint):
        super().__init__(name='goToFreeDepot')
        self.name = 'goToFreeDepot'
        self.isRootTask = True
        self.closestFreeDepotCoordinate: Optional[Coordinate] = None
        self.terminable = False
        self.delayOfTimeout = 120.0
        self.timeout_config_path = 'ng_runtime.task_timeouts.goToFreeDepot'
        self.timeout_env_var = 'FENRIL_GO_TO_FREE_DEPOT_TIMEOUT'
        self.timeout_default = 120.0
        self.shouldTimeoutTreeWhenTimeout = True
        self.waypoint = waypoint
        self.state = 'findingVisibleCoordinates'
        self.visitedOrBusyCoordinates: Dict[Coordinate, bool] = {}
        self.hasNoFreeDepotCoordinatesVar = False

    def shouldRestart(self, _: Waypoint) -> bool:
        options = self.waypoint.get('options') if isinstance(self.waypoint, dict) else None
        city = options.get('city') if isinstance(options, dict) else None
        if len(self.tasks) == 0 and self.hasNoFreeDepotCoordinatesVar == True and city == 'Dark Mansion':
            return True
        else:
            return False
        
    def onBeforeRestart(self, context: Waypoint) -> Context:
        self.onBeforeStart(context)
        return context

    # TODO: add unit tests
    def onBeforeStart(self, context: Context) -> Context:
        options = self.waypoint.get('options') if isinstance(self.waypoint, dict) else None
        city = options.get('city') if isinstance(options, dict) else None
        cities_any = cast(Dict[str, Dict[str, Any]], cities)
        city_data: Dict[str, Any] = {}
        depotCoordinates_any: Any = []
        depot_goals: Any = None

        # Prefer explicit city when provided, but keep scripts working even when
        # city isn't set by inferring depot coordinates from all known cities.
        if city and city in cities_any:
            city_data = cities_any.get(city, {})
            depotCoordinates_any = city_data.get('depotCoordinates', [])
            depot_goals = city_data.get('depotGoalCoordinates')
        else:
            if city:
                log('warn', f"goToFreeDepot: unknown waypoint.options.city {city!r}; inferring from visible depots")
            else:
                log('warn', "goToFreeDepot: missing waypoint.options.city; inferring from visible depots")
            all_depots: list = []
            for _name, _data in cities_any.items():
                coords = _data.get('depotCoordinates')
                if isinstance(coords, list):
                    all_depots.extend(coords)
            depotCoordinates_any = all_depots

        coordinate = context['ng_radar']['coordinate']
        visibleDepotCoordinates = self.getVisibleDepotCoordinates(coordinate, depotCoordinates_any)
        if len(visibleDepotCoordinates) > 0:
            self.state = 'walkingIntoFreeDepot'
            freeDepotCoordinates = self.getFreeDepotCoordinates(context['gameWindow']['players'], visibleDepotCoordinates)
            hasNoFreeDepotCoordinates = len(freeDepotCoordinates) == 0
            self.hasNoFreeDepotCoordinatesVar = hasNoFreeDepotCoordinates
            if hasNoFreeDepotCoordinates:
                if city == 'Dark Mansion':
                    return context
                self.state = 'walkingIntoVisibleCoordinates'
                for visibleDepotCoordinate in visibleDepotCoordinates:
                    self.visitedOrBusyCoordinates[visibleDepotCoordinate] = True
                return context
            current = np.array(coordinate, dtype=np.float32)
            options_arr = np.array(freeDepotCoordinates, dtype=np.float32)
            diffs = options_arr - current
            dist2 = np.sum(diffs * diffs, axis=1)
            closestFreeDepotCoordinateIndex = int(np.argmin(dist2))
            self.closestFreeDepotCoordinate = freeDepotCoordinates[closestFreeDepotCoordinateIndex]
            
            # Provide a goal coordinate for OpenLockerTask.
            # If the city has a specific mapping use it; otherwise fallback to using
            # the depot coordinate itself (many depots are clickable directly).
            if self.closestFreeDepotCoordinate is not None:
                locker_goal = None
                if isinstance(depot_goals, dict):
                    locker_goal = depot_goals.get(self.closestFreeDepotCoordinate)
                context['ng_deposit']['lockerCoordinate'] = locker_goal or self.closestFreeDepotCoordinate

            if self.closestFreeDepotCoordinate is None:
                self.terminable = True
                return context

            walkpoints = generateFloorWalkpoints(coordinate, self.closestFreeDepotCoordinate)
            self.tasks = [WalkTask(context, walkpoint).setParentTask(self).setRootTask(self.rootTask) for walkpoint in walkpoints]
        else:
            self.state = 'walkingIntoVisibleCoordinates'
            # - gerar caminho até visualizar os próximos depots se necessário
        # -- Se sim
        # --- gerar caminho até a coordenada. Ficar pingando para verificar se alguem entra nesse tempo, cancela e calcula novamente.
        # -- Se não
        # - marcar as coordenadas atuais como ocupadas
        # - começar de novo
        # Observação: ao saber que todas as coordenadas estão ocupadas, marcar todas como não ocupadas, parar o boneco e ficar verificando se sai ou alguem, ou se começa o novo tempo de ronda
        return context

    # TODO: add unit tests
    def getFreeDepotCoordinates(self, battleListPlayers: CreatureList, visibleDepotCoordinates: CoordinateList) -> CoordinateList:
        if len(battleListPlayers) == 0:
            return visibleDepotCoordinates
        # battleListPlayersCoordinates = [playerCoordinate for playerCoordinate in battleListPlayers['coordinate'].tolist()]
        battleListPlayersCoordinates: CoordinateList = []
        for player in battleListPlayers:
            try:
                c = player.get('coordinate') if isinstance(player, dict) else None
                if isinstance(c, (list, tuple)) and len(c) >= 3:
                    battleListPlayersCoordinates.append((int(c[0]), int(c[1]), int(c[2])))
            except Exception:
                continue

        delta = set(battleListPlayersCoordinates)
        return [x for x in visibleDepotCoordinates if x not in delta]

    # TODO: add unit tests
    def getVisibleDepotCoordinates(self, coordinate: Coordinate, depotCoordinates: Any) -> CoordinateList:
        visible: CoordinateList = []
        if not isinstance(depotCoordinates, list):
            return visible
        for depotCoordinate in depotCoordinates:
            if not isinstance(depotCoordinate, (list, tuple)) or len(depotCoordinate) < 3:
                continue
            try:
                c: Coordinate = (int(depotCoordinate[0]), int(depotCoordinate[1]), int(depotCoordinate[2]))
            except Exception:
                continue
            if c[0] >= (coordinate[0] - 7) and c[0] <= (coordinate[0] + 7) and c[1] >= (coordinate[1] - 5) and c[1] <= (coordinate[1] + 5):
                visible.append(c)
        return visible

    # TODO: add unit tests
    # TODO: not working
    def ping(self, context: Context) -> Context:
        if self.closestFreeDepotCoordinate is None:
            return context
        if self.state == 'walkingIntoFreeDepot' and context['ng_radar']['coordinate'][0] == self.closestFreeDepotCoordinate[0] and context['ng_radar']['coordinate'][1] == self.closestFreeDepotCoordinate[1]:
            self.terminable = True
            options = self.waypoint.get('options') if isinstance(self.waypoint, dict) else None
            city = options.get('city') if isinstance(options, dict) else None
            cities_any = cast(Dict[str, Dict[str, Any]], cities)
            if city and city in cities_any:
                city_data = cities_any.get(city, {})
                depot_goals = city_data.get('depotGoalCoordinates')
                if isinstance(depot_goals, dict):
                    context['ng_deposit']['lockerCoordinate'] = depot_goals.get(self.closestFreeDepotCoordinate) or self.closestFreeDepotCoordinate
                else:
                    context['ng_deposit']['lockerCoordinate'] = self.closestFreeDepotCoordinate
            else:
                context['ng_deposit']['lockerCoordinate'] = self.closestFreeDepotCoordinate
        return context
