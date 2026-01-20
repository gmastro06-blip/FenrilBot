from nptyping import NDArray
from typing import Any, List, Literal, Tuple, TypeAlias, Union


BBox: TypeAlias = Tuple[int, int, int, int]
Coordinate: TypeAlias = Tuple[int, int, int]
CoordinateList: TypeAlias = List[Coordinate]
CreatureCategory = str
CreatureCategoryOrUnknown = Union[CreatureCategory, Literal['unknown']]
Direction = Literal['up', 'down', 'left', 'right']
# TODO: fix it
GrayImage: TypeAlias = NDArray[Any, Any]
GrayPixel: TypeAlias = int
# TODO: fix it
GrayVector: TypeAlias = NDArray[Any, Any]
Slot: TypeAlias = Tuple[int, int]
SlotWidth: TypeAlias = Literal[32, 64]
Waypoint = Any
WaypointList: TypeAlias = List[Waypoint]
XYCoordinate: TypeAlias = Tuple[int, int]
XYCoordinateList: TypeAlias = List[XYCoordinate]