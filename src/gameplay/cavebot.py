import os
from typing import Union
from src.repositories.gameWindow.creatures import hasTargetToCreature
from .core.tasks.attackClosestCreature import AttackClosestCreatureTask
from .typings import Context
from src.utils.runtime_settings import get_bool

# HARDENING STATUS: Target management improved (2026-01-28)
# ✅ Explicitly clears dead target (targetCreature = None)
# ✅ Logs when no closestCreature (visibility into idle state)
# ✅ Battle list fallback for flaky on-screen detection
# ✅ Attack task reset bounded (70 ticks → press ESC)
# 
# OPTIONAL IMPROVEMENT: Consider battle list as primary source
#   Set FENRIL_ATTACK_FROM_BATTLELIST=true for more reliability
#   See: HARDENING_RECOMMENDATIONS.md Section 4


# TODO: add unit tests
def resolveCavebotTasks(context: Context) -> Union[AttackClosestCreatureTask, None]:
    currentTask = context['ng_tasksOrchestrator'].getCurrentTask(context)
    if context['ng_cave']['isAttackingSomeCreature']:
        if context['ng_cave']['targetCreature'] is None:
            # Some themes/capture pipelines make battle list "being attacked" detection flaky.
            # In battle-list fallback mode, don't stall here; keep trying to acquire a target.
            bl_creatures = context.get('ng_battleList', {}).get('creatures')
            bl_count = len(bl_creatures) if bl_creatures is not None else 0
            if bl_count > 0 and get_bool(context, 'ng_runtime.attack_from_battlelist', env_var='FENRIL_ATTACK_FROM_BATTLELIST', default=False):
                try:
                    from src.repositories.battleList.selection import choose_target_index

                    idx, _, _ = choose_target_index(context)
                except Exception:
                    idx = None
                if idx is None:
                    return context
                context['ng_tasksOrchestrator'].setRootTask(
                    context, AttackClosestCreatureTask())
            return context
        if hasTargetToCreature(
                context['gameWindow']['monsters'], context['ng_cave']['targetCreature'], context['ng_radar']['coordinate']) == False:
            # HARDENING: Target muerto/desaparecido - limpiar y retarget
            context['ng_cave']['targetCreature'] = None
            
            if context['ng_cave']['closestCreature'] is None:
                # HARDENING: No hay closestCreature, pero puede haber mobs.
                # Forzar re-scan en siguiente tick en vez de quedarse idle
                from src.utils.console_log import log_throttled
                log_throttled(
                    'cavebot.retarget_needed',
                    'warn',
                    'Cavebot: Target lost and no closestCreature. Waiting for next scan.',
                    5.0
                )
                return context
            context['ng_tasksOrchestrator'].setRootTask(
                context, AttackClosestCreatureTask())
            return context
        if currentTask is None or context['ng_tasksOrchestrator'].rootTask.name != 'attackClosestCreature':
            context['ng_tasksOrchestrator'].setRootTask(
                context, AttackClosestCreatureTask())
        return context
    if context['ng_cave']['closestCreature'] is None:
        bl_creatures = context.get('ng_battleList', {}).get('creatures')
        bl_count = len(bl_creatures) if bl_creatures is not None else 0
        if bl_count > 0 and get_bool(context, 'ng_runtime.attack_from_battlelist', env_var='FENRIL_ATTACK_FROM_BATTLELIST', default=False):
            try:
                from src.repositories.battleList.selection import choose_target_index

                idx, _, _ = choose_target_index(context)
            except Exception:
                idx = None
            if idx is None:
                return context
            context['ng_tasksOrchestrator'].setRootTask(
                context, AttackClosestCreatureTask())
        return context
    context['ng_tasksOrchestrator'].setRootTask(
        context, AttackClosestCreatureTask())
    return context


# TODO: add unit tests
def shouldAskForCavebotTasks(context: Context) -> bool:
    if context['way'] != 'ng_cave':
        return False
    currentTask = context['ng_tasksOrchestrator'].getCurrentTask(context)
    if currentTask is None:
        return True
    return (currentTask.name not in ['dropFlasks', 'lootCorpse', 'moveDown', 'moveUp', 'singleMove', 'rightClickDirection', 'refillChecker', 'singleWalk', 'refillChecker', 'useRopeWaypoint', 'useShovelWaypoint', 'rightClickUseWaypoint', 'openDoor', 'useLadderWaypoint'])
