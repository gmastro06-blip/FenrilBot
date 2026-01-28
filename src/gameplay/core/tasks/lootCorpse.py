from typing import Any

from ...typings import Context
from .common.vector import VectorTask
from .walkToCoordinate import WalkToCoordinateTask
from .collectDeadCorpse import CollectDeadCorpseTask
from .openBackpack import OpenBackpackTask


class LootCorpseTask(VectorTask):
    def __init__(self: "LootCorpseTask", creature: Any) -> None:
        super().__init__()
        self.name = 'lootCorpse'
        self.isRootTask = True
        self.creature = creature

    def onBeforeStart(self, context: Context) -> Context:
        from src.utils.coordinate import is_valid_coordinate
        coord = None
        try:
            if isinstance(self.creature, dict):
                coord = self.creature.get('coordinate')
        except Exception:
            coord = None

        self.tasks = []
        # Always ensure backpacks are open before attempting to loot.
        # Free-account looting (open+drag) requires the loot backpack window to be visible.
        try:
            main_bp = context.get('ng_backpacks', {}).get('main')
            loot_bp = context.get('ng_backpacks', {}).get('loot')
            if main_bp:
                self.tasks.append(OpenBackpackTask(main_bp).setParentTask(self).setRootTask(self))
            if loot_bp:
                self.tasks.append(OpenBackpackTask(loot_bp).setParentTask(self).setRootTask(self))
        except Exception:
            pass
        if is_valid_coordinate(coord):
            try:
                walk_coord = (int(coord[0]), int(coord[1]), int(coord[2]))
            except Exception:
                walk_coord = None
            if walk_coord is not None:
                self.tasks.append(WalkToCoordinateTask(walk_coord).setParentTask(self).setRootTask(self))
        self.tasks.append(CollectDeadCorpseTask(self.creature).setParentTask(self).setRootTask(self))
        return context
