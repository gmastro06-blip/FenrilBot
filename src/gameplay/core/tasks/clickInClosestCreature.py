import os

import src.utils.keyboard as keyboard
import src.utils.mouse as mouse
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.repositories.battleList import extractors as battlelist_extractors
from src.shared.typings import XYCoordinate

class ClickInClosestCreatureTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'clickInClosestCreature'
        self.delayOfTimeout = 1

    def _with_modifier_click(self, coord: XYCoordinate) -> None:
        modifier = os.getenv('FENRIL_ATTACK_CLICK_MODIFIER', 'ctrl').strip().lower()
        if modifier in {'none', 'no', '0', ''}:
            mouse.leftClick(coord)
            return

        # Tibia default (non-classic controls) usually requires Ctrl+Click to attack.
        # Keep it configurable for different control schemes.
        keyboard.keyDown(modifier)
        mouse.leftClick(coord)
        keyboard.keyUp(modifier)

    def shouldIgnore(self, context: Context) -> bool:
        return context['ng_cave']['targetCreature'] is not None

    def did(self, context: Context) -> bool:
        return context['ng_cave']['isAttackingSomeCreature'] == True

    def do(self, context: Context) -> Context:
        ng_cave = context.get('ng_cave', {})
        ng_targeting = context.get('ng_targeting', {})
        game_window = context.get('gameWindow', {})
        if ng_cave.get('isAttackingSomeCreature', False) == False:
            closest_creature = ng_cave.get('closestCreature')
            if closest_creature and closest_creature.get('windowCoordinate'):
                # Primary: click the closest creature on screen (capture-local coords).
                self._with_modifier_click(closest_creature['windowCoordinate'])
                if isinstance(context.get('ng_debug'), dict):
                    context['ng_debug']['last_tick_reason'] = 'attack click: closestCreature'
                return context

            # Fallback: click the first creature in battle list, if we can locate it.
            if context.get('ng_screenshot') is not None:
                battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=0)
                if battle_click is not None:
                    self._with_modifier_click(battle_click)
                    if isinstance(context.get('ng_debug'), dict):
                        context['ng_debug']['last_tick_reason'] = 'attack click: battleList[0]'
                    return context

            # Last resort: send a hotkey (user-configurable).
            hotkey = os.getenv('FENRIL_ATTACK_HOTKEY', 'space')
            keyboard.press(hotkey)
            if isinstance(context.get('ng_debug'), dict):
                context['ng_debug']['last_tick_reason'] = f'attack hotkey: {hotkey}'

        return context