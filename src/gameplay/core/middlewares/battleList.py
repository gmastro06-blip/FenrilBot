import numpy as np
import os

from src.repositories.battleList.core import getCreatures, isAttackingSomeCreature
from src.repositories.battleList.extractors import getContent
from src.repositories.battleList.locators import getBattleListIconPosition, getContainerBottomBarPosition
from src.repositories.battleList.typings import Creature
from src.utils.console_log import log_throttled
from ...typings import Context


# TODO: add unit tests
def setBattleListMiddleware(context: Context) -> Context:
    screenshot = context.get('ng_screenshot')
    content = getContent(screenshot) if screenshot is not None else None
    context['ng_battleList']['creatures'] = (
        getCreatures(content) if content is not None else np.array([], dtype=Creature)
    )

    if (
        os.getenv('FENRIL_WARN_ON_BATTLELIST_EMPTY', '1') in {'1', 'true', 'True'}
        and screenshot is not None
        and content is not None
        and len(context['ng_battleList']['creatures']) == 0
    ):
        log_throttled(
            'battleList.empty',
            'warn',
            'Battle list detected but has 0 entries. Check Tibia battle list filters (Players/NPCs/Monsters) and ensure the list is visible in the capture.',
            10.0,
        )

    # Extra diagnostics: when the bot never attacks, the root cause is often that
    # the capture does not include the battle list (or it can't be matched).
    if os.getenv('FENRIL_TARGETING_DIAG', '0') in {'1', 'true', 'True'}:
        dbg = context.get('ng_debug')
        if not isinstance(dbg, dict):
            dbg = {}
            context['ng_debug'] = dbg

        icon_pos = getBattleListIconPosition(screenshot) if screenshot is not None else None
        dbg['battleList_icon_found'] = icon_pos is not None
        dbg['battleList_content_found'] = content is not None

        raw_list = None
        bottom_pos = None
        if screenshot is not None and icon_pos is not None:
            raw_list = screenshot[
                icon_pos[1] + icon_pos[3] + 1:,
                icon_pos[0] - 1:icon_pos[0] - 1 + 156,
            ]
            bottom_pos = getContainerBottomBarPosition(raw_list)

        dbg['battleList_bottomBar_found'] = bottom_pos is not None
        dbg['battleList_raw_shape'] = getattr(raw_list, 'shape', None)
        dbg['battleList_content_shape'] = getattr(content, 'shape', None)

        log_throttled(
            'battleList.diag',
            'info',
            f"battleList: icon={dbg['battleList_icon_found']} content={dbg['battleList_content_found']} bottom={dbg['battleList_bottomBar_found']}",
            2.0,
        )

    context['ng_cave']['isAttackingSomeCreature'] = isAttackingSomeCreature(
        context['ng_battleList']['creatures'])
    return context
