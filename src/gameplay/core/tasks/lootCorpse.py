from typing import Any

from ...typings import Context
from .common.vector import VectorTask
from .walkToCoordinate import WalkToCoordinateTask
from .collectDeadCorpse import CollectDeadCorpseTask


class LootCorpseTask(VectorTask):
    def __init__(self: "LootCorpseTask", creature: Any) -> None:
        super().__init__()
        self.name = 'lootCorpse'
        self.isRootTask = True
        self.creature = creature

    def onBeforeStart(self, context: Context) -> Context:
        coord = None
        try:
            if isinstance(self.creature, dict):
                coord = self.creature.get('coordinate')
        except Exception:
            coord = None

        self.tasks = []
        if isinstance(coord, (list, tuple)) and len(coord) >= 3:
            try:
                walk_coord = (int(coord[0]), int(coord[1]), int(coord[2]))
            except Exception:
                walk_coord = None
            if walk_coord is not None:
                self.tasks.append(WalkToCoordinateTask(walk_coord).setParentTask(self).setRootTask(self))
        self.tasks.append(CollectDeadCorpseTask(self.creature).setParentTask(self).setRootTask(self))
        return context
