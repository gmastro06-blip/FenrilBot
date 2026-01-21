import pyautogui
from time import sleep, time
import traceback
import sys
import os
from typing import TYPE_CHECKING, Any, Callable, Optional, cast

from src.gameplay.typings import Context as GameplayContext
from src.gameplay.cavebot import resolveCavebotTasks, shouldAskForCavebotTasks
from src.gameplay.combo import comboSpells
from src.gameplay.core.middlewares.battleList import setBattleListMiddleware
from src.gameplay.core.middlewares.chat import setChatTabsMiddleware
from src.gameplay.core.middlewares.gameWindow import setDirectionMiddleware, setGameWindowCreaturesMiddleware, setGameWindowMiddleware, setHandleLootMiddleware
from src.gameplay.core.middlewares.playerStatus import setMapPlayerStatusMiddleware
from src.gameplay.core.middlewares.statsBar import setMapStatsBarMiddleware
from src.gameplay.core.middlewares.radar import setRadarMiddleware, setWaypointIndexMiddleware
from src.gameplay.core.middlewares.screenshot import setScreenshotMiddleware
from src.gameplay.core.middlewares.window import setTibiaWindowMiddleware
from src.gameplay.core.middlewares.tasks import setCleanUpTasksMiddleware
from src.gameplay.core.tasks.lootCorpse import LootCorpseTask
from src.gameplay.resolvers import resolveTasksByWaypoint
from src.gameplay.healing.observers.eatFood import eatFood
from src.gameplay.healing.observers.autoHur import autoHur
from src.gameplay.healing.observers.clearPoison import clearPoison
from src.gameplay.healing.observers.healingBySpells import healingBySpells
from src.gameplay.healing.observers.healingByPotions import healingByPotions
from src.gameplay.healing.observers.healingByMana import healingByMana
from src.gameplay.healing.observers.swapAmulet import swapAmulet
from src.gameplay.healing.observers.swapRing import swapRing
from src.gameplay.targeting import hasCreaturesToAttack
from src.repositories.battleList import extractors as battlelist_extractors
from src.repositories.gameWindow.creatures import getClosestCreature, getTargetCreature
from src.gameplay.core.tasks.attackClosestCreature import AttackClosestCreatureTask

from src.utils.console_log import log, log_throttled

if TYPE_CHECKING:
    from src.ui.context import Context as UIContext

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

class PilotNGThread:
    # TODO: add typings
    def __init__(self, context: "UIContext") -> None:
        self.context = context
        self._last_reason = None

    def mainloop(self) -> None:
        while True:
            try:
                if self.context.context.get('ng_should_stop'):
                    break
                if 'ng_debug' not in self.context.context:
                    self.context.context['ng_debug'] = {'last_tick_reason': None, 'last_exception': None}
                if self.context.context['ng_pause']:
                    self.context.context['ng_debug']['last_tick_reason'] = 'paused'
                    log_throttled('pilot.status.paused', 'info', 'Paused (ng_pause=1)', float(os.getenv('FENRIL_STATUS_LOG_INTERVAL', '2.0')))
                    sleep(1)
                    continue
                startTime = time()
                self.context.context = self.handleGameData(
                    self.context.context)
                self.context.context = self.handleGameplayTasks(
                    self.context.context)
                self.context.context = self.context.context['ng_tasksOrchestrator'].do(
                    self.context.context)

                # Periodic status line to make it obvious why cavebot isn't acting.
                interval = float(os.getenv('FENRIL_STATUS_LOG_INTERVAL', '2.0'))
                dbg = self.context.context.get('ng_debug', {})
                reason = dbg.get('last_tick_reason')
                cave = self.context.context.get('ng_cave', {})
                coord = self.context.context.get('ng_radar', {}).get('coordinate')
                current_task = None
                try:
                    current_task = self.context.context['ng_tasksOrchestrator'].getCurrentTask(self.context.context)
                except Exception:
                    current_task = None

                root_name = None
                task_name = None
                try:
                    if current_task is not None:
                        task_name = getattr(current_task, 'name', None)
                        root = getattr(current_task, 'rootTask', None)
                        root_name = getattr(root, 'name', None) if root is not None else None
                except Exception:
                    pass

                status_msg = (
                    f"cave_enabled={cave.get('enabled')} runToCreatures={cave.get('runToCreatures')} "
                    f"way={self.context.context.get('way')} coord={coord} "
                    f"task={task_name} root={root_name} reason={reason}"
                )

                if os.getenv('FENRIL_WINDOW_DIAG', '0') in {'1', 'true', 'True'}:
                    status_msg += (
                        f" action_title={dbg.get('action_window_title')!r}"
                        f" capture_title={dbg.get('capture_window_title')!r}"
                        f" cap_rect={self.context.context.get('ng_capture_rect')}"
                        f" act_rect={self.context.context.get('ng_action_rect')}"
                    )
                log_throttled('pilot.status', 'info', status_msg, interval)
                if reason != self._last_reason and reason is not None:
                    self._last_reason = reason
                    log('info', f"Tick reason changed: {reason}")

                self.context.context['ng_radar']['lastCoordinateVisited'] = self.context.context['ng_radar']['coordinate']
                healingByPotions(self.context.context)
                healingByMana(self.context.context)
                healingBySpells(self.context.context)
                comboSpells(self.context.context)
                swapAmulet(self.context.context)
                swapRing(self.context.context)
                clearPoison(self.context.context)
                autoHur(self.context.context)
                eatFood(self.context.context)
                endTime = time()
                diff = endTime - startTime
                sleep(max(0.045 - diff, 0))
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                if 'ng_debug' not in self.context.context:
                    self.context.context['ng_debug'] = {'last_tick_reason': None, 'last_exception': None}
                self.context.context['ng_debug']['last_exception'] = f"{type(e).__name__}: {e}"
                log('error', f"Exception: {type(e).__name__}: {e}")
                log('error', traceback.format_exc())

    def handleGameData(self, context: GameplayContext) -> GameplayContext:
        if context['ng_pause']:
            return context
        # Resolve action/capture windows (dual-window support) before grabbing screenshots.
        context = setTibiaWindowMiddleware(context)
        context = setScreenshotMiddleware(context)
        context = setRadarMiddleware(context)
        context = setChatTabsMiddleware(context)
        context = setBattleListMiddleware(context)
        context = setGameWindowMiddleware(context)
        context = setDirectionMiddleware(context)
        context = setGameWindowCreaturesMiddleware(context)
        if context['ng_cave']['enabled'] and context['ng_cave']['runToCreatures'] == True:
            context = setHandleLootMiddleware(context)          
        else:
            get_target_creature = cast(
                Callable[[list[dict[str, Any]]], Optional[dict[str, Any]]],
                getTargetCreature,
            )
            context['ng_cave']['targetCreature'] = get_target_creature(
                cast(list[dict[str, Any]], context['gameWindow']['monsters'])
            )
        context = setWaypointIndexMiddleware(context)
        context = setMapPlayerStatusMiddleware(context)
        context = setMapStatsBarMiddleware(context)
        context = setCleanUpTasksMiddleware(context)
        return context

    def handleGameplayTasks(self, context: GameplayContext) -> GameplayContext:
        # TODO: func to check if coord is none
        # If we temporarily modified cavebot behavior due to missing radar,
        # restore it as soon as radar comes back.
        allow_attack = os.getenv('FENRIL_ALLOW_ATTACK_WITHOUT_COORD', '0') in {'1', 'true', 'True'}
        if allow_attack and context.get('ng_radar', {}).get('coordinate') is not None:
            diag = context.get('ng_diag') if isinstance(context.get('ng_diag'), dict) else None
            if isinstance(diag, dict) and diag.get('forced_runToCreatures') is True:
                saved = diag.get('saved_runToCreatures')
                if isinstance(context.get('ng_cave'), dict):
                    if isinstance(saved, bool):
                        context['ng_cave']['runToCreatures'] = saved
                    diag['forced_runToCreatures'] = False

        if context['ng_radar']['coordinate'] is None:
            if not allow_attack:
                if 'ng_debug' in context and isinstance(context['ng_debug'], dict):
                    # Preserve a more specific reason from middlewares (e.g. "radar tools not found").
                    prev = context['ng_debug'].get('last_tick_reason')
                    if prev in (None, 'running', 'no coord'):
                        context['ng_debug']['last_tick_reason'] = 'no coord'
                return context

            # Attack-only fallback: allow targeting/clicking even when radar is missing.
            # This is useful for stationary hunting or when minimap/radar templates are hidden.
            try:
                if isinstance(context.get('ng_cave'), dict):
                    diag = context.get('ng_diag') if isinstance(context.get('ng_diag'), dict) else None
                    if isinstance(diag, dict) and diag.get('forced_runToCreatures') is not True:
                        diag['saved_runToCreatures'] = bool(context['ng_cave'].get('runToCreatures', True))
                        diag['forced_runToCreatures'] = True
                    context['ng_cave']['runToCreatures'] = False
            except Exception:
                pass

            hasCreaturesToAttackAfterCheck = hasCreaturesToAttack(context)

            # Manual auto-attack does not require radar. If enabled, keep running the attack task tree
            # even when detection is empty so PageUp/other hotkeys keep firing.
            manual_cfg = context.get('manual_auto_attack') if isinstance(context, dict) else None
            manual_enabled_cfg = isinstance(manual_cfg, dict) and bool(manual_cfg.get('enabled', False))
            manual_enabled_env = os.getenv('FENRIL_MANUAL_AUTO_ATTACK', '0') in {'1', 'true', 'True'}
            if manual_enabled_cfg or manual_enabled_env:
                hasCreaturesToAttackAfterCheck = True
            if hasCreaturesToAttackAfterCheck:
                context['way'] = 'ng_cave'
                # In manual mode, schedule attackClosestCreature directly to keep hotkey loop active.
                if manual_enabled_cfg or manual_enabled_env:
                    try:
                        currentTask = context['ng_tasksOrchestrator'].getCurrentTask(context)
                    except Exception:
                        currentTask = None
                    currentRootTask = currentTask.rootTask if currentTask is not None else None
                    if currentRootTask is None or getattr(currentRootTask, 'name', None) != 'attackClosestCreature':
                        context['ng_tasksOrchestrator'].setRootTask(context, AttackClosestCreatureTask())
                else:
                    if shouldAskForCavebotTasks(context):
                        currentTask = context['ng_tasksOrchestrator'].getCurrentTask(context)
                        currentRootTask = currentTask.rootTask if currentTask is not None else None
                        isTryingToAttackClosestCreature = currentRootTask is not None and (
                            currentRootTask.name == 'attackClosestCreature')
                        if not isTryingToAttackClosestCreature:
                            context = resolveCavebotTasks(context)
                if 'ng_debug' in context and isinstance(context['ng_debug'], dict):
                    prev = context['ng_debug'].get('last_tick_reason')
                    if prev in (None, 'running', 'no coord'):
                        context['ng_debug']['last_tick_reason'] = 'no coord (attack fallback)'
            else:
                if 'ng_debug' in context and isinstance(context['ng_debug'], dict):
                    prev = context['ng_debug'].get('last_tick_reason')
                    if prev in (None, 'running', 'no coord'):
                        context['ng_debug']['last_tick_reason'] = 'no coord (attack fallback idle)'

            try:
                context['gameWindow']['previousMonsters'] = context['gameWindow']['monsters']
            except Exception:
                pass
            return context
        if any(coord is None for coord in context['ng_radar']['coordinate']):
            if 'ng_debug' in context and isinstance(context['ng_debug'], dict):
                prev = context['ng_debug'].get('last_tick_reason')
                if prev in (None, 'running', 'partial coord'):
                    context['ng_debug']['last_tick_reason'] = 'partial coord'
            return context

        # Attack-only mode: never follow waypoints; only try to acquire/keep a target.
        # This is intended for stationary hunting setups and supervised runs.
        if os.getenv('FENRIL_ATTACK_ONLY', '0') in {'1', 'true', 'True'}:
            try:
                context['ng_cave']['closestCreature'] = getClosestCreature(
                    context['gameWindow']['monsters'], context['ng_radar']['coordinate'])
            except Exception:
                pass

            should_attack = hasCreaturesToAttack(context)

            # If manual auto-attack is enabled, always schedule the attack task tree so
            # the hotkey/cursor-click loop can run even when detection returns 0.
            manual_cfg = context.get('manual_auto_attack') if isinstance(context, dict) else None
            manual_enabled_cfg = isinstance(manual_cfg, dict) and bool(manual_cfg.get('enabled', False))
            manual_enabled_env = os.getenv('FENRIL_MANUAL_AUTO_ATTACK', '0') in {'1', 'true', 'True'}
            if manual_enabled_cfg or manual_enabled_env:
                should_attack = True
            if not should_attack and os.getenv('FENRIL_ATTACK_FROM_BATTLELIST', '0') in {'1', 'true', 'True'}:
                try:
                    if context.get('ng_screenshot') is not None:
                        battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=0)
                        if battle_click is not None:
                            should_attack = True
                except Exception:
                    pass

            if should_attack:
                context['way'] = 'ng_cave'
                # In attack-only/manual modes we want to schedule the attack task tree even when
                # detection is flaky (bl=0, monsters=0). Avoid resolveCavebotTasks() gating.
                try:
                    currentTask = context['ng_tasksOrchestrator'].getCurrentTask(context)
                except Exception:
                    currentTask = None
                currentRootTask = currentTask.rootTask if currentTask is not None else None
                if currentRootTask is None or getattr(currentRootTask, 'name', None) != 'attackClosestCreature':
                    context['ng_tasksOrchestrator'].setRootTask(context, AttackClosestCreatureTask())
                if 'ng_debug' in context and isinstance(context['ng_debug'], dict):
                    prev = context['ng_debug'].get('last_tick_reason')
                    if prev in (None, 'running', 'attack-only'):
                        context['ng_debug']['last_tick_reason'] = 'attack-only'
            else:
                if 'ng_debug' in context and isinstance(context['ng_debug'], dict):
                    prev = context['ng_debug'].get('last_tick_reason')
                    if prev in (None, 'running', 'attack-only idle'):
                        context['ng_debug']['last_tick_reason'] = 'attack-only idle'

            try:
                context['gameWindow']['previousMonsters'] = context['gameWindow']['monsters']
            except Exception:
                pass
            return context
        if not context.get('ng_cave', {}).get('waypoints', {}).get('items'):
            if 'ng_debug' in context:
                context['ng_debug']['last_tick_reason'] = 'no waypoints'
            return context
        context['ng_cave']['closestCreature'] = getClosestCreature(
            context['gameWindow']['monsters'], context['ng_radar']['coordinate'])
        currentTask = context['ng_tasksOrchestrator'].getCurrentTask(context)
        if currentTask is not None and currentTask.name == 'selectChatTab':
            if 'ng_debug' in context:
                context['ng_debug']['last_tick_reason'] = 'selectChatTab'
            return context
        if len(context['loot']['corpsesToLoot']) > 0 and context['ng_cave']['runToCreatures'] == True and context['ng_cave']['enabled']:
            context['way'] = 'lootCorpses'
            if currentTask is not None and currentTask.rootTask is not None and currentTask.rootTask.name != 'lootCorpse':
                context['ng_tasksOrchestrator'].setRootTask(context, None)
            if context['ng_tasksOrchestrator'].getCurrentTask(context) is None:
                # TODO: get closest dead corpse
                firstDeadCorpse = context['loot']['corpsesToLoot'][0]
                context['ng_tasksOrchestrator'].setRootTask(
                    context, LootCorpseTask(firstDeadCorpse))
            context['gameWindow']['previousMonsters'] = context['gameWindow']['monsters']
            return context
        if context['ng_cave']['runToCreatures'] == True and context['ng_cave']['enabled']:
            hasCreaturesToAttackAfterCheck = hasCreaturesToAttack(context)

            # Optional diagnostics to understand "not attacking" reports.
            if os.getenv('FENRIL_TARGETING_DIAG', '0') in {'1', 'true', 'True'}:
                monsters = context.get('gameWindow', {}).get('monsters') or []
                bl_creatures = context.get('ng_battleList', {}).get('creatures')
                bl_count = len(bl_creatures) if bl_creatures is not None else 0
                dbg = context.get('ng_debug') if isinstance(context.get('ng_debug'), dict) else {}
                closest = context.get('ng_cave', {}).get('closestCreature')
                target = context.get('ng_cave', {}).get('targetCreature')
                attacking = bool(context.get('ng_cave', {}).get('isAttackingSomeCreature', False))
                can_ignore = context.get('ng_targeting', {}).get('canIgnoreCreatures')
                has_ignorable = context.get('ng_targeting', {}).get('hasIgnorableCreatures')
                log_throttled(
                    'pilot.targeting.diag',
                    'info',
                    f"targeting: monsters={len(monsters)} bl={bl_count} blIcon={dbg.get('battleList_icon_found')} blContent={dbg.get('battleList_content_found')} blBottom={dbg.get('battleList_bottomBar_found')} hasCreaturesToAttack={hasCreaturesToAttackAfterCheck} attacking={attacking} canIgnore={can_ignore} hasIgnorable={has_ignorable} closest={getattr(closest, 'get', lambda _k, _d=None: None)('name', None) if closest else None} target={getattr(target, 'get', lambda _k, _d=None: None)('name', None) if target else None}",
                    2.0,
                )

            if hasCreaturesToAttackAfterCheck:
                if context['ng_cave']['closestCreature'] is not None:
                    context['way'] = 'ng_cave'
                else:
                    # If battle list has entries and the user enabled battle list
                    # fallback, treat it as a cavebot (attack) situation.
                    bl_creatures = context.get('ng_battleList', {}).get('creatures')
                    bl_count = len(bl_creatures) if bl_creatures is not None else 0
                    if bl_count > 0 and os.getenv('FENRIL_ATTACK_FROM_BATTLELIST', '0') in {'1', 'true', 'True'}:
                        context['way'] = 'ng_cave'
                    else:
                        context['way'] = 'waypoint'
            else:
                context['way'] = 'waypoint'
            if hasCreaturesToAttackAfterCheck and shouldAskForCavebotTasks(context):
                currentRootTask = currentTask.rootTask if currentTask is not None else None
                isTryingToAttackClosestCreature = currentRootTask is not None and (
                    currentRootTask.name == 'attackClosestCreature')
                if not isTryingToAttackClosestCreature:
                    context = resolveCavebotTasks(context)
            elif context['way'] == 'waypoint':
                if context['ng_tasksOrchestrator'].getCurrentTask(context) is None:
                    currentWaypointIndex = context['ng_cave']['waypoints']['currentIndex']
                    if currentWaypointIndex is None:
                        if 'ng_debug' in context:
                            context['ng_debug']['last_tick_reason'] = 'no currentIndex'
                        return context
                    currentWaypoint = context['ng_cave']['waypoints']['items'][currentWaypointIndex]
                    context['ng_tasksOrchestrator'].setRootTask(
                        context, resolveTasksByWaypoint(currentWaypoint))
                    if 'ng_debug' in context:
                        context['ng_debug']['last_tick_reason'] = f"set task: {currentWaypoint.get('type', '?')}"
        elif context['ng_cave']['enabled'] and context['ng_tasksOrchestrator'].getCurrentTask(context) is None:
                currentWaypointIndex = context['ng_cave']['waypoints']['currentIndex']
                if currentWaypointIndex is not None:
                    currentWaypoint = context['ng_cave']['waypoints']['items'][currentWaypointIndex]
                    context['ng_tasksOrchestrator'].setRootTask(
                        context, resolveTasksByWaypoint(currentWaypoint))
                    if 'ng_debug' in context:
                        context['ng_debug']['last_tick_reason'] = f"set task: {currentWaypoint.get('type', '?')}"

        context['gameWindow']['previousMonsters'] = context['gameWindow']['monsters']
        if 'ng_debug' in context and context['ng_debug'].get('last_tick_reason') in (None, 'selectChatTab'):
            context['ng_debug']['last_tick_reason'] = 'running'
        return context
