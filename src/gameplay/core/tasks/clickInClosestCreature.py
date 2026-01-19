import src.utils.keyboard as keyboard
import src.utils.mouse as mouse
from src.gameplay.typings import Context
from .common.base import BaseTask

class ClickInClosestCreatureTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'clickInClosestCreature'
        self.delayOfTimeout = 1

    def shouldIgnore(self, context: Context) -> bool:
        return context['ng_cave']['targetCreature'] is not None

    def did(self, context: Context) -> bool:
        return context['ng_cave']['isAttackingSomeCreature'] == True

    def do(self, context: Context) -> Context:
        ng_cave = context.get('ng_cave', {})
        ng_targeting = context.get('ng_targeting', {})
        game_window = context.get('gameWindow', {})
        if ng_cave.get('isAttackingSomeCreature', False) == False:
            # TODO: find another way (maybe click in battle)
            # attack by mouse click when there are players on screen or ignorable creatures
            if game_window.get('players', []) or ng_targeting.get('hasIgnorableCreatures', False):
                closest_creature = ng_cave.get('closestCreature')
                if closest_creature and closest_creature.get('windowCoordinate'):
                    keyboard.keyDown('alt')
                    mouse.leftClick(closest_creature['windowCoordinate'])
                    keyboard.keyUp('alt')
                return context
            keyboard.press('space')

        return context