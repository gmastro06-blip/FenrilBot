from src.shared.typings import Coordinate
from src.gameplay.typings import Context
from .common.vector import VectorTask
from .setNextWaypoint import SetNextWaypointTask
from .walkToCoordinate import WalkToCoordinateTask
from .attackMonstersBox import AttackMonstersBoxTask
from .lootMonstersBox import LootMonstersBoxTask
from .resetSpellIndex import ResetSpellIndexTask
from .sayPlayerAfterBox import SayPlayerAfterBoxTask

class WalkToWaypointTask(VectorTask):
    def __init__(self, coordinate: Coordinate, ignore: bool = False, passinho: bool = False):
        super().__init__()
        self.name = 'walkToWaypoint'
        self.delayAfterComplete = 1
        self.isRootTask = True
        self.coordinate = coordinate
        self.ignore = ignore
        self.passinho = passinho

    def onBeforeStart(self, context: Context) -> Context:
        runToCreatures = context.get('ng_cave', {}).get('runToCreatures', True)
        if runToCreatures == True or self.ignore == True:
            self.tasks = [
                WalkToCoordinateTask(self.coordinate, self.passinho).setParentTask(self).setRootTask(self),
                SetNextWaypointTask().setParentTask(self).setRootTask(self),
            ]
        else:
            self.tasks = [
                WalkToCoordinateTask(self.coordinate).setParentTask(self).setRootTask(self),
                AttackMonstersBoxTask().setParentTask(self).setRootTask(self),
                LootMonstersBoxTask().setParentTask(self).setRootTask(self),
                LootMonstersBoxTask().setParentTask(self).setRootTask(self),
                LootMonstersBoxTask().setParentTask(self).setRootTask(self),
                ResetSpellIndexTask().setParentTask(self).setRootTask(self),
                SayPlayerAfterBoxTask().setParentTask(self).setRootTask(self),
                SetNextWaypointTask().setParentTask(self).setRootTask(self),
            ]
        return context
