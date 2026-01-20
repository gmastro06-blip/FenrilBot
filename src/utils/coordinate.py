from numba import njit
import numpy as np
from scipy.spatial import distance
from typing import Any, Union
from src.shared.typings import Coordinate, CoordinateList, XYCoordinate


# TODO: add unit tests
def getAroundPixelsCoordinates(pixelCoordinate: XYCoordinate) -> np.ndarray:
    aroundPixelsCoordinatesIndexes = np.array(
        [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]])
    pixelCoordinates = np.broadcast_to(
        pixelCoordinate, aroundPixelsCoordinatesIndexes.shape)
    return np.add(aroundPixelsCoordinatesIndexes, pixelCoordinates)


# TODO: add unit tests
def getAvailableAroundPixelsCoordinates(aroundPixelsCoordinates: Any, walkableFloorSqms: np.ndarray) -> np.ndarray:
    yPixelsCoordinates = aroundPixelsCoordinates[:, 1]
    xPixelsCoordinates = aroundPixelsCoordinates[:, 0]
    nonzero = np.nonzero(
        walkableFloorSqms[yPixelsCoordinates, xPixelsCoordinates])[0]
    return np.take(
        aroundPixelsCoordinates, nonzero, axis=0)


# TODO: add unit tests
def getAvailableAroundCoordinates(coordinate: Coordinate, walkableFloorSqms: np.ndarray) -> np.ndarray:
    pixelCoordinate = getPixelFromCoordinate(coordinate)
    aroundPixelsCoordinates = getAroundPixelsCoordinates(pixelCoordinate)
    availableAroundPixelsCoordinates = getAvailableAroundPixelsCoordinates(
        aroundPixelsCoordinates, walkableFloorSqms)
    xCoordinates = availableAroundPixelsCoordinates[:, 0] + 31744
    yCoordinates = availableAroundPixelsCoordinates[:, 1] + 30976
    floors = np.broadcast_to(
        coordinate[2], (availableAroundPixelsCoordinates.shape[0]))
    return np.column_stack(
        (xCoordinates, yCoordinates, floors))


def getClosestCoordinate(coordinate: Coordinate, coordinates: Any) -> Coordinate:
    coordinateWithoutFloor = (coordinate[0], coordinate[1])
    coordinatesWithoutFloor = [(x[0], x[1]) for x in coordinates]
    distancesOfCoordinates = distance.cdist(
        [coordinateWithoutFloor], coordinatesWithoutFloor)[0]
    closestCoordinateIndex = np.argsort(distancesOfCoordinates)[0]
    return coordinates[closestCoordinateIndex]


def getCoordinateFromPixel(pixel: XYCoordinate) -> XYCoordinate:
    return pixel[0] + 31744, pixel[1] + 30976


def getDirectionBetweenCoordinates(coordinate: Coordinate, nextCoordinate: Coordinate) -> Union[str, None]:
    if coordinate[0] < nextCoordinate[0]:
        return 'right'
    if nextCoordinate[0] < coordinate[0]:
        return 'left'
    if coordinate[1] < nextCoordinate[1]:
        return 'down'
    if nextCoordinate[1] < coordinate[1]:
        return 'up'
    return None


@njit(cache=True, fastmath=True)
def getPixelFromCoordinate(coordinate: Coordinate) -> XYCoordinate:
    return coordinate[0] - 31744, coordinate[1] - 30976
