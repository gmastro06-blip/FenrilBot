import pytest

from src.gameplay.resolvers import resolveTasksByWaypoint
from src.gameplay.core.tasks.depositGold import DepositGoldTask
from src.gameplay.core.tasks.depositItems import DepositItemsTask
from src.gameplay.core.tasks.depositItemsHouse import DepositItemsHouseTask
from src.gameplay.core.tasks.refill import RefillTask
from src.gameplay.core.tasks.refillChecker import RefillCheckerTask


@pytest.mark.parametrize(
    "waypoint, expected_type",
    [
        ({"type": "depositGold"}, DepositGoldTask),
        ({"type": "depositItems"}, DepositItemsTask),
        ({"type": "depositItemsHouse"}, DepositItemsHouseTask),
        ({"type": "refill"}, RefillTask),
        ({"type": "refillChecker"}, RefillCheckerTask),
    ],
)
def test_resolveTasksByWaypoint_deposit_refill_mapping(waypoint, expected_type):
    task = resolveTasksByWaypoint(waypoint)
    assert isinstance(task, expected_type)
