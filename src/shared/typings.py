from nptyping import NDArray
from typing import Any, List, Literal, Tuple, Union


BBox = Tuple[int, int, int, int]
Coordinate = Tuple[int, int, int]
CoordinateList = List[Coordinate]
CreatureCategory = str
CreatureCategoryOrUnknown = Union[CreatureCategory, Literal['unknown']]
Direction = Literal['up', 'down', 'left', 'right']
# TODO: fix it
GrayImage = NDArray[Any, Any]
GrayPixel = int
# TODO: fix it
GrayVector = NDArray[Any, Any]
Slot = Tuple[int, int]
SlotWidth = 32 | 64
Waypoint = Any
WaypointList = List[Waypoint]
XYCoordinate = Tuple[int, int]
XYCoordinateList = List[XYCoordinate]