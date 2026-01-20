import numpy as np
import src.gameplay.utils as gameplayUtils
from src.repositories.radar.core import getBreakpointTileMovementSpeed, getTileFrictionByCoordinate
from src.repositories.skills.core import getSpeed
from src.shared.typings import Coordinate
from src.utils.coordinate import getDirectionBetweenCoordinates
from src.utils.keyboard import press
from ...typings import Context
from .common.base import BaseTask


class SingleWalkPressTask(BaseTask):
    def __init__(self: "SingleWalkPressTask", context: Context, coordinate: Coordinate) -> None:
        super().__init__()
        self.name = 'singleWalkPress'
        charSpeed = getSpeed(context['ng_screenshot']) or 0
        tileFriction = getTileFrictionByCoordinate(coordinate)
        movementSpeed = getBreakpointTileMovementSpeed(
            charSpeed, tileFriction)
        self.delayOfTimeout = (movementSpeed * 2) / 1000
        self.coordinate = coordinate

    # TODO: add unit tests
    def shouldIgnore(self, context: Context) -> bool:
        # TODO: improve clever code
        isStartingFromLastCoordinate = (context['ng_radar']['lastCoordinateVisited'] is None or np.any(
            context['ng_radar']['coordinate'] == context['ng_radar']['lastCoordinateVisited']) == True) == False
        return isStartingFromLastCoordinate

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        direction = getDirectionBetweenCoordinates(
            context['ng_radar']['coordinate'], self.coordinate)
        if direction is None:
            return context
        press(direction)
        return context

    # TODO: add unit tests
    def did(self, context: Context) -> bool:
        return gameplayUtils.coordinatesAreEqual(context['ng_radar']['coordinate'], self.coordinate)
