from numba import njit
import numpy as np
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
    if coordinates is None or len(coordinates) == 0:
        return coordinate

    target_xy = np.array([coordinate[0], coordinate[1]], dtype=np.int64)
    coords_xy = np.array([(int(c[0]), int(c[1])) for c in coordinates], dtype=np.int64)
    diffs = coords_xy - target_xy
    dist2 = (diffs[:, 0] * diffs[:, 0]) + (diffs[:, 1] * diffs[:, 1])
    closest_index = int(np.argmin(dist2))
    return coordinates[closest_index]


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
