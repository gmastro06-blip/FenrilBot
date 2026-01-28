from src.repositories.battleList.core import getBeingAttackedCreatureCategory
from src.repositories.chat.core import hasNewLoot
from src.repositories.gameWindow.config import gameWindowSizes
from src.repositories.gameWindow.core import getCoordinate, getImageByCoordinate
from src.repositories.gameWindow.creatures import getCreatures, getCreaturesByType, getDifferentCreaturesBySlots, getTargetCreature
from ...comboSpells.core import spellsPath
from ...typings import Context
from ..tasks.selectChatTab import SelectChatTabTask
from src.utils.console_log import log_throttled
from src.utils.runtime_settings import get_bool, get_float

import time


# TODO: add unit tests
def setDirectionMiddleware(context: Context) -> Context:
    if context['ng_radar']['previousCoordinate'] is None:
        context['ng_radar']['previousCoordinate'] = context['ng_radar']['coordinate']

    if (context['ng_radar']['coordinate'] is not None and
            context['ng_radar']['previousCoordinate'] is not None):
        if (context['ng_radar']['coordinate'][0] != context['ng_radar']['previousCoordinate'][0] or
                context['ng_radar']['coordinate'][1] != context['ng_radar']['previousCoordinate'][1] or
                context['ng_radar']['coordinate'][2] != context['ng_radar']['previousCoordinate'][2]):

            comingFromDirection = None
            if context['ng_radar']['coordinate'][2] != context['ng_radar']['previousCoordinate'][2]:
                comingFromDirection = None
            elif (context['ng_radar']['coordinate'][0] != context['ng_radar']['previousCoordinate'][0] and
                context['ng_radar']['coordinate'][1] != context['ng_radar']['previousCoordinate'][1]):
                comingFromDirection = None
            elif context['ng_radar']['coordinate'][0] != context['ng_radar']['previousCoordinate'][0]:
                comingFromDirection = 'left' if context['ng_radar']['coordinate'][0] > context['ng_radar']['previousCoordinate'][0] else 'right'
            elif context['ng_radar']['coordinate'][1] != context['ng_radar']['previousCoordinate'][1]:
                comingFromDirection = 'top' if context['ng_radar']['coordinate'][1] > context['ng_radar']['previousCoordinate'][1] else 'bottom'
            
            context['ng_comingFromDirection'] = comingFromDirection

    # if context['gameWindow']['previousGameWindowImage'] is not None:
    #     context['gameWindow']['walkedPixelsInSqm'] = getWalkedPixels(context)

    context['gameWindow']['previousGameWindowImage'] = context['gameWindow']['image']
    context['ng_radar']['previousCoordinate'] = context['ng_radar']['coordinate']
    return context


# TODO: add unit tests
def setHandleLootMiddleware(context: Context) -> Context:
    log_loot = get_bool(
        context,
        'ng_runtime.log_loot',
        env_var='FENRIL_LOG_LOOT',
        default=False,
        prefer_env=True,
    )
    currentTaskName = context['ng_tasksOrchestrator'].getCurrentTaskName(context)
    if (currentTaskName not in ['depositGold', 'refill', 'buyBackpack', 'selectChatTab', 'travel']):
        lootTab = context['ng_chat']['tabs'].get('loot')
        if lootTab is not None and not lootTab['isSelected']:
            context['ng_tasksOrchestrator'].setRootTask(
                context, SelectChatTabTask('loot'))
    loot_chat = hasNewLoot(context['ng_screenshot'])
    skip_loot_chat = False
    if loot_chat:
        # MEDIO 2.2: Debounce por hash de contenido, no solo por timestamp
        try:
            import hashlib
            loot_tab_msgs = context.get('ng_chat', {}).get('tabs', {}).get('loot', {}).get('messages', [])
            # Hash del último mensaje de loot para evitar duplicados
            last_msg = str(loot_tab_msgs[-1] if loot_tab_msgs else '')
            msg_hash = hashlib.md5(last_msg.encode()).hexdigest()
            last_hash = context.get('ng_cave', {}).get('_last_loot_msg_hash')
            if last_hash == msg_hash:
                skip_loot_chat = True
            else:
                context.setdefault('ng_cave', {})['_last_loot_msg_hash'] = msg_hash
        except Exception:
            # Fallback a timestamp si el hash falla
            try:
                now = time.time()
                last_ts = context.get('ng_cave', {}).get('_last_loot_chat_ts')
                if isinstance(last_ts, (int, float)) and (now - float(last_ts)) < 1.25:
                    skip_loot_chat = True
                else:
                    context.setdefault('ng_cave', {})['_last_loot_chat_ts'] = now
            except Exception:
                pass

    if loot_chat and not skip_loot_chat:
        log_loot = get_bool(
            context,
            'ng_runtime.log_loot_events',
            env_var='FENRIL_LOG_LOOT_EVENTS',
            default=False,
        )

        radar_state = context.get('ng_radar')
        if not isinstance(radar_state, dict):
            radar_state = {}
        radar_coord = radar_state.get('coordinate') or radar_state.get('previousCoordinate')

        # Primary signal: last known target creature.
        corpse = context['ng_cave'].get('previousTargetCreature')
        # Fallback: current target creature (can still be selected when loot message arrives).
        if corpse is None:
            corpse = context['ng_cave'].get('targetCreature')

        if corpse is not None:
            # Mark a death/loot event so later in this middleware we can force-clear
            # the target for at least one tick (avoids phantom targeting/attacking).
            context.setdefault('ng_cave', {})['_force_clear_target_once'] = True
            context['loot']['corpsesToLoot'].append(corpse)
            context['ng_cave']['previousTargetCreature'] = None
            if log_loot:
                name = None
                try:
                    if isinstance(corpse, dict):
                        name = corpse.get('name')
                        coord = corpse.get('coordinate')
                except Exception:
                    name = None
                    coord = None
                log_throttled(
                    'loot.chat.queued',
                    'info',
                    f"Death/loot event: queued corpse from target ({name or 'unknown'}) at {coord} (queue size: {len(context['loot']['corpsesToLoot'])})",
                    0.5,
                )
        else:
            # Fallback: we got a loot message but couldn't resolve the on-screen target.
            # Still trigger a single loot around the player (CollectDeadCorpseTask loots the 3x3 area).
            # To avoid repeated looting forever, enqueue a synthetic corpse with the player's coordinate
            # so CollectDeadCorpseTask.onComplete can remove it after one attempt.

            # IMPORTANT: Guard against stale/duplicate loot lines being detected while idle.
            # When we cannot resolve a corpse/target, only enqueue fallback loot if we were in combat
            # recently (configurable). This prevents the bot from getting wedged in lootCorpses from
            # old loot history.
            try:
                require_combat = get_bool(
                    context,
                    'ng_runtime.loot_fallback_requires_combat',
                    env_var='FENRIL_LOOT_FALLBACK_REQUIRES_COMBAT',
                    default=True,
                    prefer_env=True,
                )
                if require_combat:
                    now = time.time()
                    last_combat = context.get('ng_cave', {}).get('_last_combat_ts')
                    window_s = get_float(
                        context,
                        'ng_runtime.loot_fallback_combat_window_s',
                        env_var='FENRIL_LOOT_FALLBACK_COMBAT_WINDOW_S',
                        default=25.0,
                        prefer_env=True,
                    )
                    if not isinstance(last_combat, (int, float)) or (now - float(last_combat)) > float(window_s):
                        if log_loot:
                            log_throttled(
                                'loot.chat.fallback.ignored_idle',
                                'warn',
                                'Loot signal detected but no target resolved; ignoring fallback loot because no recent combat (likely stale chat)',
                                5.0,
                            )
                        corpse = None
                        # Skip the fallback enqueue below.
                        radar_coord = None
            except Exception:
                pass

            from src.utils.coordinate import is_valid_coordinate
            fallback_name = None
            dbg = context.get('ng_debug')
            if isinstance(dbg, dict):
                fallback_name = dbg.get('battleList_target_name') or None
                # Only set the reason if we actually enqueue fallback loot.

            # Usar is_valid_coordinate para validación consistente
            radar_coord = context.get('ng_radar', {}).get('coordinate')
            if is_valid_coordinate(radar_coord):
                try:
                    corpse_fallback = {
                        'name': str(fallback_name) if fallback_name else 'unknown',
                        'coordinate': (int(radar_coord[0]), int(radar_coord[1]), int(radar_coord[2])),
                    }
                    context.setdefault('ng_cave', {})['_force_clear_target_once'] = True
                    context['loot']['corpsesToLoot'].append(corpse_fallback)
                    if isinstance(dbg, dict):
                        dbg['last_tick_reason'] = 'loot msg detected but no target creature (fallback loot)'
                    if log_loot:
                        log_throttled(
                            'loot.chat.fallback.queued',
                            'info',
                            f"Death/loot event: no target resolved; queued fallback loot at player ({corpse_fallback['name']})",
                            0.5,
                        )
                except Exception:
                    pass
            else:
                if log_loot:
                    log_throttled(
                        'loot.chat.invalid_coord',
                        'warn',
                        'Loot signal detected but radar coordinate is invalid; ignoring',
                        2.0,
                    )

            if log_loot:
                if is_valid_coordinate(radar_coord):
                    msg = 'Death/loot event: loot signal detected but no target creature found; using fallback loot near player'
                else:
                    msg = 'Loot signal detected but no target and no radar coordinate; ignoring (likely stale chat)'
                log_throttled('loot.chat.no_target', 'warn', msg, 2.0)
        # has spelled exori category
        if context['ng_comboSpells']['lastUsedSpell'] is not None and context['ng_comboSpells']['lastUsedSpell'] in ['exori', 'exori gran', 'exori mas']:
            spellPath = spellsPath.get(
                context['ng_comboSpells']['lastUsedSpell'], [])
            if len(spellPath) > 0:
                differentCreatures = getDifferentCreaturesBySlots(
                    context['gameWindow']['previousMonsters'], context['gameWindow']['monsters'], spellPath)
                for creature in differentCreatures:
                    context['loot']['corpsesToLoot'].append(creature)
            context['ng_comboSpells']['lastUsedSpell'] = None
            context['ng_comboSpells']['lastUsedSpellAt'] = None

    # Fallback loot trigger: if loot chat detection is unreliable (capture/crop/theme),
    # still try to loot when a fight just ended.
    try:
        now = time.time()
        attacking = bool(context.get('ng_cave', {}).get('isAttackingSomeCreature', False))
        tgt = context.get('ng_cave', {}).get('targetCreature')
        if tgt is None:
            # Sometimes visual target detection lags even while battle list shows we're attacking.
            # Use the last known target as a better fallback for death/loot handling.
            tgt = context.get('ng_cave', {}).get('previousTargetCreature')
        if attacking and tgt is not None:
            context['ng_cave']['_last_attack_ts'] = now
            context['ng_cave']['_last_attack_target'] = tgt

        # If we were attacking recently and are no longer attacking, queue one corpse.
        last_ts = context.get('ng_cave', {}).get('_last_attack_ts')
        last_tgt = context.get('ng_cave', {}).get('_last_attack_target')
        if (
            (not attacking)
            and isinstance(last_ts, (int, float))
            and (now - float(last_ts)) <= 3.0
            and last_tgt is not None
        ):
            context['loot']['corpsesToLoot'].append(last_tgt)
            context.setdefault('ng_cave', {})['_force_clear_target_once'] = True
            # Clear so we don't enqueue repeatedly.
            context['ng_cave']['_last_attack_ts'] = None
            context['ng_cave']['_last_attack_target'] = None
            dbg = context.get('ng_debug')
            if isinstance(dbg, dict):
                dbg['last_tick_reason'] = 'loot fallback: fight ended'
            if get_bool(
                context,
                'ng_runtime.log_loot_events',
                env_var='FENRIL_LOG_LOOT_EVENTS',
                default=False,
            ):
                name = None
                try:
                    if isinstance(last_tgt, dict):
                        name = last_tgt.get('name')
                except Exception:
                    name = None
                log_throttled(
                    'loot.fallback.queued',
                    'info',
                    f"Death/fight-end event: queued corpse fallback ({name or 'unknown'})",
                    0.5,
                )
    except Exception:
        pass

    # Update targetCreature. If a death/loot event was detected this tick, force-clear
    # target once (prevents "phantom" targeting persisting after a kill).
    force_clear = bool(context.get('ng_cave', {}).pop('_force_clear_target_once', False))
    if force_clear:
        context['ng_cave']['targetCreature'] = None
        dbg = context.get('ng_debug')
        if isinstance(dbg, dict):
            # Keep existing reason if set to something more specific.
            dbg.setdefault('last_tick_reason', 'death event: cleared target')
        if get_bool(
            context,
            'ng_runtime.log_loot_events',
            env_var='FENRIL_LOG_LOOT_EVENTS',
            default=False,
        ):
            log_throttled('loot.death.clear_target', 'info', 'Death event: cleared current target', 0.5)
    else:
        context['ng_cave']['targetCreature'] = getTargetCreature(
            context['gameWindow']['monsters'])
        if context['ng_cave']['targetCreature'] is not None:
            context['ng_cave']['previousTargetCreature'] = context['ng_cave']['targetCreature']
    return context


# TODO: add unit tests
def setGameWindowMiddleware(context: Context) -> Context:
    if context['ng_screenshot'] is None:
        context['gameWindow']['coordinate'] = None
        context['gameWindow']['image'] = None
        return context
    context['gameWindow']['coordinate'] = getCoordinate(
        context['ng_screenshot'], (gameWindowSizes[1080][0], gameWindowSizes[1080][1]))
    if context['gameWindow']['coordinate'] is None:
        context['gameWindow']['image'] = None
        return context
    context['gameWindow']['image'] = getImageByCoordinate(
        context['ng_screenshot'], context['gameWindow']['coordinate'], (gameWindowSizes[1080][0], gameWindowSizes[1080][1]))
    return context


# TODO: add unit tests
def setGameWindowCreaturesMiddleware(context: Context) -> Context:
    context['ng_battleList']['beingAttackedCreatureCategory'] = getBeingAttackedCreatureCategory(
        context['ng_battleList']['creatures'])
    # TODO: func to check if coord is none
    if context['ng_radar']['coordinate'] is None:
        return context
    if any(coord is None for coord in context['ng_radar']['coordinate']):
        return context
    context['gameWindow']['creatures'] = getCreatures(
        context['ng_battleList']['creatures'], context['ng_comingFromDirection'], context['gameWindow']['coordinate'], context['gameWindow']['image'], context['ng_radar']['coordinate'], beingAttackedCreatureCategory=context['ng_battleList']['beingAttackedCreatureCategory'], walkedPixelsInSqm=context['gameWindow']['walkedPixelsInSqm'])
    if len(context['gameWindow']['creatures']) == 0:
        context['gameWindow']['monsters'] = []
        context['gameWindow']['players'] = []
        return context
    context['gameWindow']['monsters'] = getCreaturesByType(
        context['gameWindow']['creatures'], 'monster')
    context['gameWindow']['players'] = getCreaturesByType(
        context['gameWindow']['creatures'], 'player')
    return context
