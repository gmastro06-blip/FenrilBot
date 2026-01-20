import src.gameplay.utils as gameplayUtils
from src.repositories.radar.core import getBreakpointTileMovementSpeed, getTileFrictionByCoordinate
from src.repositories.skills.core import getSpeed
from src.shared.typings import Coordinate
from src.utils.coordinate import getDirectionBetweenCoordinates
from src.utils.keyboard import keyDown, press
from ...typings import Context
from ...utils import releaseKeys
from .common.base import BaseTask


class WalkTask(BaseTask):
    walkpoint: Coordinate

    def __init__(self: "WalkTask", context: Context, coordinate: Coordinate, passinho: bool = False) -> None:
        super().__init__()
        self.name = 'walk'
        charSpeed = getSpeed(context['ng_screenshot']) or 0
        tileFriction = getTileFrictionByCoordinate(coordinate)
        movementSpeed = getBreakpointTileMovementSpeed(
            charSpeed, tileFriction)
        self.delayOfTimeout = (movementSpeed * 2) / 1000
        # TODO: fix passinho with char speed
        self.delayBeforeStart = (movementSpeed * 2) / 1000 if passinho == True else 0
        self.shouldTimeoutTreeWhenTimeout = True
        self.walkpoint = coordinate

    # TODO: add unit tests
    def shouldIgnore(self, context: Context) -> bool:
        if context['ng_radar']['lastCoordinateVisited'] is None:
            return True
        if context['ng_radar']['coordinate'] is None:
            return True
        return not gameplayUtils.coordinatesAreEqual(context['ng_radar']['coordinate'], context['ng_radar']['lastCoordinateVisited'])

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        current = context['ng_radar']['coordinate']
        if current is None:
            return context
        direction = getDirectionBetweenCoordinates(
            current, self.walkpoint)
        if direction is None:
            return context
        parent = self.parentTask
        futureDirection = None
        if parent is not None and len(parent.tasks) > 1:
            if parent.currentTaskIndex + 1 < len(parent.tasks):
                next_walkpoint = parent.tasks[parent.currentTaskIndex + 1].walkpoint
                if next_walkpoint is not None:
                    futureDirection = getDirectionBetweenCoordinates(
                        self.walkpoint, next_walkpoint)
        if direction != futureDirection:
            if context['ng_lastPressedKey'] is not None:
                context = releaseKeys(context)
            else:
                press(direction)
            return context
        if direction != context['ng_lastPressedKey']:
            if parent is not None and len(parent.tasks) > 2:
                keyDown(direction)
                context['ng_lastPressedKey'] = direction
            else:
                press(direction)
            return context
        if parent is not None and len(parent.tasks) == 1 and context['ng_lastPressedKey'] is not None:
            context = releaseKeys(context)
        return context

    # TODO: add unit tests
    def did(self, context: Context) -> bool:
        if context['ng_radar']['coordinate'] is None:
            return False
        return gameplayUtils.coordinatesAreEqual(context['ng_radar']['coordinate'], self.walkpoint)

    # TODO: add unit tests
    def onInterrupt(self, context: Context) -> Context:
        return releaseKeys(context)

    # TODO: add unit tests
    def onTimeout(self, context: Context) -> Context:
        return releaseKeys(context)
