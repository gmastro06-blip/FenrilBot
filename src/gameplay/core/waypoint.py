import tcod
from src.repositories.radar.config import walkableFloorsSqms
from src.shared.typings import Coordinate, CoordinateList
from src.utils.coordinate import getAvailableAroundCoordinates, getClosestCoordinate, getPixelFromCoordinate
from .typings import Checkpoint
from typing import Any, Optional, cast


# TODO: add unit tests
def generateFloorWalkpoints(
    coordinate: Coordinate,
    goalCoordinate: Coordinate,
    nonWalkableCoordinates: Optional[CoordinateList] = None,
) -> CoordinateList:
    if nonWalkableCoordinates is None:
        nonWalkableCoordinates = []
    pixelCoordinate = getPixelFromCoordinate(coordinate)
    xFromTheStartOfRadar = pixelCoordinate[0] - 53
    xFromTheEndOfRadar = pixelCoordinate[0] + 53
    yFromTheStartOfRadar = pixelCoordinate[1] - 54
    yFromTheEndOfRadar = pixelCoordinate[1] + 55
    copiedWalkableFloorSqms = walkableFloorsSqms[coordinate[2]][
        yFromTheStartOfRadar:yFromTheEndOfRadar, xFromTheStartOfRadar:xFromTheEndOfRadar].copy()
    for nonWalkableCoordinate in nonWalkableCoordinates:
        if nonWalkableCoordinate[2] == coordinate[2]:
            nonWalkableCoordinateInPixelX, nonWalkableCoordinateInPixelY = getPixelFromCoordinate(nonWalkableCoordinate)
            leX = nonWalkableCoordinateInPixelX - xFromTheStartOfRadar
            leY = nonWalkableCoordinateInPixelY - yFromTheStartOfRadar
            if leX >= 0 and leX <= 106 and leY >= 0 and leY <= 109:
                copiedWalkableFloorSqms[leY, leX] = 0
    x = goalCoordinate[0] - coordinate[0] + 53
    y = goalCoordinate[1] - coordinate[1] + 54
    return [
        (coordinate[0] + x - 53, coordinate[1] + y - 54, coordinate[2])
        for y, x in tcod.path.AStar(copiedWalkableFloorSqms, 0).get_path(54, 53, y, x)
    ]


# TODO: add unit tests
def resolveFloorCoordinate(_context: Any, nextCoordinate: Coordinate) -> Checkpoint:
    return {
        'goalCoordinate': nextCoordinate,
        'checkInCoordinate': nextCoordinate,
    }


# TODO: add types
# TODO: add unit tests
def resolveMoveDownCoordinate(_context: Any, waypoint: Any) -> Checkpoint:
    checkInCoordinate: Coordinate
    if waypoint['options']['direction'] == 'north':
        checkInCoordinate = (
            waypoint['coordinate'][0],
            waypoint['coordinate'][1] - 2,
            waypoint['coordinate'][2] + 1,
        )
    elif waypoint['options']['direction'] == 'south':
        checkInCoordinate = (
            waypoint['coordinate'][0],
            waypoint['coordinate'][1] + 2,
            waypoint['coordinate'][2] + 1,
        )
    elif waypoint['options']['direction'] == 'east':
        checkInCoordinate = (
            waypoint['coordinate'][0] + 2,
            waypoint['coordinate'][1],
            waypoint['coordinate'][2] + 1,
        )
    else:
        checkInCoordinate = (
            waypoint['coordinate'][0] - 2,
            waypoint['coordinate'][1],
            waypoint['coordinate'][2] + 1,
        )
    goal = cast(Coordinate, tuple(waypoint['coordinate']))
    return {
        'goalCoordinate': goal,
        'checkInCoordinate': checkInCoordinate,
    }


# TODO: add types
# TODO: add unit tests
def resolveMoveUpCoordinate(_context: Any, waypoint: Any) -> Checkpoint:
    checkInCoordinate: Coordinate
    if waypoint['options']['direction'] == 'north':
        checkInCoordinate = (
            waypoint['coordinate'][0],
            waypoint['coordinate'][1] - 2,
            waypoint['coordinate'][2] - 1,
        )
    elif waypoint['options']['direction'] == 'south':
        checkInCoordinate = (
            waypoint['coordinate'][0],
            waypoint['coordinate'][1] + 2,
            waypoint['coordinate'][2] - 1,
        )
    elif waypoint['options']['direction'] == 'east':
        checkInCoordinate = (
            waypoint['coordinate'][0] + 2,
            waypoint['coordinate'][1],
            waypoint['coordinate'][2] - 1,
        )
    else:
        checkInCoordinate = (
            waypoint['coordinate'][0] - 2,
            waypoint['coordinate'][1],
            waypoint['coordinate'][2] - 1,
        )
    goal = cast(Coordinate, tuple(waypoint['coordinate']))
    return {
        'goalCoordinate': goal,
        'checkInCoordinate': checkInCoordinate,
    }


# TODO: add unit tests
def resolveUseShovelWaypointCoordinate(coordinate: Coordinate, nextCoordinate: Coordinate) -> Checkpoint:
    availableAroundCoordinates = getAvailableAroundCoordinates(
        nextCoordinate, walkableFloorsSqms[nextCoordinate[2]])
    closestCoordinate = getClosestCoordinate(
        coordinate, availableAroundCoordinates)
    checkInCoordinate: Coordinate = (nextCoordinate[0], nextCoordinate[1], nextCoordinate[2] + 1)
    return {
        'goalCoordinate': closestCoordinate,
        'checkInCoordinate': checkInCoordinate,
    }


# TODO: add unit tests
def resolveUseRopeWaypointCoordinate(_context: Any, nextCoordinate: Coordinate) -> Checkpoint:
    return {
        'goalCoordinate': (nextCoordinate[0], nextCoordinate[1], nextCoordinate[2]),
        'checkInCoordinate': (nextCoordinate[0], nextCoordinate[1] + 1, nextCoordinate[2] - 1),
    }


# TODO: add unit tests
def resolveUseHoleCoordinate(_context: Any, nextCoordinate: Coordinate) -> Checkpoint:
    return {
        'goalCoordinate': nextCoordinate,
        'checkInCoordinate': (nextCoordinate[0], nextCoordinate[1], nextCoordinate[2] + 1),
    }


# TODO: add unit tests
def resolveGoalCoordinate(coordinate: Coordinate, waypoint: Any) -> Checkpoint:
    if waypoint['type'] == 'useRope':
        return resolveUseRopeWaypointCoordinate(coordinate, cast(Coordinate, tuple(waypoint['coordinate'])))
    if waypoint['type'] == 'useShovel':
        return resolveUseShovelWaypointCoordinate(coordinate, cast(Coordinate, tuple(waypoint['coordinate'])))
    if waypoint['type'] == 'moveDown':
        return resolveMoveDownCoordinate(coordinate, waypoint)
    if waypoint['type'] == 'moveUp':
        return resolveMoveUpCoordinate(coordinate, waypoint)
    if waypoint['type'] == 'useHole':
        return resolveUseHoleCoordinate(coordinate, cast(Coordinate, tuple(waypoint['coordinate'])))
    return resolveFloorCoordinate(coordinate, cast(Coordinate, tuple(waypoint['coordinate'])))
