import os

from .typings import Context


# TODO: add unit tests
def hasCreaturesToAttack(context: Context) -> bool:
    context['ng_targeting']['hasIgnorableCreatures'] = False

    # Primary signal: on-screen monsters.
    if len(context['gameWindow']['monsters']) == 0:
        # Optional fallback: use battle list presence as a signal that there
        # are attackable creatures even when on-screen monster detection fails.
        # This is intentionally opt-in because the battle list can include
        # players/NPCs depending on client filters.
        bl_creatures = context.get('ng_battleList', {}).get('creatures')
        bl_count = len(bl_creatures) if bl_creatures is not None else 0
        if bl_count > 0 and os.getenv('FENRIL_ATTACK_FROM_BATTLELIST', '0') in {'1', 'true', 'True'}:
            context['ng_targeting']['canIgnoreCreatures'] = True
            return True

        context['ng_targeting']['canIgnoreCreatures'] = True
        return False
    if context['ng_targeting']['canIgnoreCreatures'] == False:
        return True
    ignorableGameWindowCreatures = []
    for gameWindowCreature in context['gameWindow']['monsters']:
        shouldIgnoreCreature = context['ng_targeting']['creatures'].get(gameWindowCreature['name'], { 'ignore': True if gameWindowCreature['name'] in context['ignorable_creatures'] else False })['ignore']
        if shouldIgnoreCreature:
            context['ng_targeting']['hasIgnorableCreatures'] = True
            ignorableGameWindowCreatures.append(gameWindowCreature)
    return len(ignorableGameWindowCreatures) < len(context['gameWindow']['monsters'])
