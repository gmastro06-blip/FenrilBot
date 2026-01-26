import time

import src.utils.keyboard as keyboard
import src.utils.mouse as mouse
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.repositories.battleList import extractors as battlelist_extractors
from src.repositories.battleList.selection import choose_target_index
from src.shared.typings import XYCoordinate
from src.utils.console_log import log_throttled
from src.utils.runtime_settings import get_bool, get_float, get_int, get_str

class ClickInClosestCreatureTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'clickInClosestCreature'
        self.delayOfTimeout = 1
        self._last_manual_attack_ts = 0.0

    def _maybe_manual_auto_attack(self, context: Context) -> bool:
        """Optional manual auto-attack mode.

        When enabled, the bot does not attempt to acquire a target. Instead it repeatedly:
        - presses a hotkey, or
        - clicks at the current cursor position

        This is useful when you want to manually aim/select targets while still having the bot
        sustain attacks.
        """

        enabled = get_bool(
            context,
            'manual_auto_attack.enabled',
            env_var='FENRIL_MANUAL_AUTO_ATTACK',
            default=False,
            prefer_env=True,
        )
        if not enabled:
            return False

        # By default, manual auto-attack runs regardless of current attacking state
        # (useful for "next target" cycling). You can restrict it if desired.
        only_when_not_attacking = get_bool(
            context,
            'manual_auto_attack.only_when_not_attacking',
            env_var='FENRIL_MANUAL_AUTO_ATTACK_ONLY_WHEN_NOT_ATTACKING',
            default=False,
            prefer_env=True,
        )
        attacking = bool(context.get('ng_cave', {}).get('isAttackingSomeCreature', False))
        if only_when_not_attacking and attacking:
            return False

        interval_s = get_float(
            context,
            'manual_auto_attack.interval_s',
            env_var='FENRIL_MANUAL_AUTO_ATTACK_INTERVAL_S',
            default=0.70,
            prefer_env=True,
        )

        now = time.time()
        if (now - self._last_manual_attack_ts) < interval_s:
            return True
        self._last_manual_attack_ts = now

        method = get_str(
            context,
            'manual_auto_attack.method',
            env_var='FENRIL_MANUAL_AUTO_ATTACK_METHOD',
            default='hotkey',
            prefer_env=True,
        ).strip().lower()

        if method in {'click', 'cursor', 'cursor_click'}:
            # Click at current cursor position.
            # NOTE: this intentionally does not move the mouse.
            modifier = get_str(
                context,
                'manual_auto_attack.click_modifier',
                env_var='FENRIL_MANUAL_AUTO_ATTACK_CLICK_MODIFIER',
                default='none',
                prefer_env=True,
            ).strip().lower()
            button = get_str(
                context,
                'manual_auto_attack.click_button',
                env_var='FENRIL_MANUAL_AUTO_ATTACK_CLICK_BUTTON',
                default='left',
                prefer_env=True,
            ).strip().lower()
            self._with_modifier_click(
                (0, 0),
                modifier=modifier,
                button=button,
                context=context,
                click_at_cursor=True,
                move_before_click=False,
            )
            if isinstance(context.get('ng_debug'), dict):
                context['ng_debug']['last_tick_reason'] = 'manual auto-attack: cursor click'
            return True

        # Default: hotkey
        hotkey = get_str(
            context,
            'manual_auto_attack.hotkey',
            env_var='FENRIL_MANUAL_AUTO_ATTACK_HOTKEY',
            default='pageup',
            prefer_env=True,
        ).strip().lower() or 'pageup'

        focus_enabled = get_bool(
            context,
            'manual_auto_attack.focus_before',
            env_var='FENRIL_FOCUS_ACTION_WINDOW_BEFORE_MANUAL_HOTKEY',
            default=False,
            prefer_env=True,
        )
        if not focus_enabled:
            # Back-compat: older env var used for attack clicks.
            focus_enabled = get_bool(
                context,
                'manual_auto_attack.focus_before',
                env_var='FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK',
                default=False,
                prefer_env=True,
            )
        if focus_enabled:
            self._focus_action_window(context)
            try:
                pre_delay_s = get_float(
                    context,
                    'manual_auto_attack.pre_delay_s',
                    env_var='FENRIL_MANUAL_AUTO_ATTACK_PRE_DELAY_S',
                    default=0.02,
                    prefer_env=True,
                )
                time.sleep(pre_delay_s)
            except Exception:
                pass

        # Optional extra reliability: repeat the key press a few times.
        repeats = get_int(
            context,
            'manual_auto_attack.key_repeat',
            env_var='FENRIL_MANUAL_AUTO_ATTACK_KEY_REPEAT',
            default=1,
            prefer_env=True,
        )
        if repeats < 1:
            repeats = 1
        if repeats > 3:
            repeats = 3
        if get_bool(context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True):
            log_throttled(
                'input.manual_attack.hotkey',
                'info',
                f"input: manual auto-attack hotkey={hotkey!r} focus={focus_enabled} repeats={repeats}",
                1.0,
            )

        for i in range(repeats):
            keyboard.press(hotkey)
            if i + 1 < repeats:
                try:
                    time.sleep(0.03)
                except Exception:
                    pass
        if isinstance(context.get('ng_debug'), dict):
            context['ng_debug']['last_tick_reason'] = f'manual auto-attack: hotkey {hotkey}'
        return True

    def _focus_action_window(self, context: Context) -> bool:
        # Default OFF to avoid stealing focus; enable explicitly when needed.
        focus_enabled = get_bool(
            context,
            'manual_auto_attack.focus_before',
            env_var='FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK',
            default=False,
            prefer_env=True,
        )
        if not focus_enabled:
            return False

        win = context.get('action_window') or context.get('window')
        if win is None:
            return False

        focused = False
        try:
            if hasattr(win, 'activate'):
                win.activate()
                focused = True
        except Exception:
            pass

        try:
            import win32con
            import win32gui

            hwnd = getattr(win, '_hWnd', None)
            if hwnd is not None:
                try:
                    # SW_RESTORE also un-maximizes a maximized window.
                    # Only restore when minimized to avoid shrinking the Tibia window.
                    if win32gui.IsIconic(hwnd):
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                except Exception:
                    pass
                try:
                    win32gui.BringWindowToTop(hwnd)
                except Exception:
                    pass
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                focused = True
        except Exception:
            pass

        if focused:
            delay_s = get_float(
                context,
                'manual_auto_attack.focus_after_s',
                env_var='FENRIL_FOCUS_AFTER_S',
                default=0.05,
                prefer_env=True,
            )
            try:
                time.sleep(delay_s)
            except Exception:
                time.sleep(0.05)
        return focused

    def _with_modifier_click(
        self,
        coord: XYCoordinate,
        *,
        modifier: str,
        button: str = 'left',
        context: Context,
        click_at_cursor: bool = False,
        move_before_click: bool = True,
    ) -> None:
        modifier = modifier.strip().lower()
        button = button.strip().lower()

        if button not in {'left', 'right'}:
            button = 'left'

        # Safety: allow users to completely disable right-click during targeting.
        # This affects ONLY this task (attack clicks), not waypoint/utility tasks.
        if get_bool(
            context,
            'ng_runtime.block_right_click_attack',
            env_var='FENRIL_BLOCK_RIGHT_CLICK_ATTACK',
            default=False,
            prefer_env=True,
        ):
            button = 'left'

        focused = self._focus_action_window(context)

        if get_bool(context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True):
            try:
                abs_coord = mouse.transform_capture_to_action(coord)
                cap_rect, act_rect = mouse.get_window_transform()
                log_throttled(
                    'input.attack.click',
                    'info',
                    f"input: attack click raw={coord} abs={abs_coord} cap_rect={cap_rect} act_rect={act_rect} modifier={modifier!r} button={button!r} focused={focused}",
                    1.0,
                )
            except Exception:
                pass

        if click_at_cursor:
            # Make the click a distinct event: move first, then click at current cursor.
            if move_before_click:
                try:
                    mouse.moveTo(coord)
                    time.sleep(
                        get_float(
                            context,
                            'ng_runtime.attack_click_pre_delay_s',
                            env_var='FENRIL_ATTACK_CLICK_PRE_DELAY_S',
                            default=0.06,
                            prefer_env=True,
                        )
                    )
                except Exception:
                    pass

        if modifier in {'none', 'no', '0', ''}:
            if button == 'right':
                mouse.rightClick(None if click_at_cursor else coord)
            else:
                mouse.leftClick(None if click_at_cursor else coord)

            if get_bool(context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True):
                try:
                    backend = mouse.get_last_click_backend()
                    log_throttled(
                        'input.attack.click.sent',
                        'info',
                        f"input: attack click sent backend={backend!r}",
                        0.5,
                    )
                except Exception:
                    pass
            return

        # Tibia default (non-classic controls) usually requires Ctrl+Click to attack.
        # Keep it configurable for different control schemes.
        keyboard.keyDown(modifier)
        if button == 'right':
            mouse.rightClick(None if click_at_cursor else coord)
        else:
            mouse.leftClick(None if click_at_cursor else coord)
        keyboard.keyUp(modifier)

        if get_bool(context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True):
            try:
                backend = mouse.get_last_click_backend()
                log_throttled(
                    'input.attack.click.sent',
                    'info',
                    f"input: attack click sent backend={backend!r}",
                    0.5,
                )
            except Exception:
                pass

    def shouldIgnore(self, context: Context) -> bool:
        return context['ng_cave']['targetCreature'] is not None

    def did(self, context: Context) -> bool:
        # In battle-list fallback mode, battle list "attacking" detection can be flaky.
        # If we don't have an actual on-screen targetCreature yet, keep trying clicks.
        if get_bool(context, 'ng_runtime.attack_from_battlelist', env_var='FENRIL_ATTACK_FROM_BATTLELIST', default=False):
            if context.get('ng_cave', {}).get('targetCreature') is None:
                bl_creatures = context.get('ng_battleList', {}).get('creatures')
                if bl_creatures is not None and len(bl_creatures) > 0:
                    return False
                # If parsing returns 0 entries, do NOT keep clicking battle list.
                # Clicking index 0 on empty lists causes "phantom attacking".
                if context.get('ng_screenshot') is not None:
                    idx, _, _ = choose_target_index(context)
                    if idx is None:
                        return context['ng_cave']['isAttackingSomeCreature'] == True
                    battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=idx)
                    if battle_click is not None:
                        return False
        return context['ng_cave']['isAttackingSomeCreature'] == True

    def do(self, context: Context) -> Context:
        ng_cave = context.get('ng_cave', {})
        ng_targeting = context.get('ng_targeting', {})
        game_window = context.get('gameWindow', {})

        attacking = bool(ng_cave.get('isAttackingSomeCreature', False))

        battle_click = None
        if get_bool(context, 'ng_runtime.attack_from_battlelist', env_var='FENRIL_ATTACK_FROM_BATTLELIST', default=False) and context.get('ng_screenshot') is not None:
            # If we can locate the battle list click coordinate and we still don't have an on-screen
            # targetCreature, treat "attacking" as untrusted and keep trying to acquire a target.
            if ng_cave.get('targetCreature') is None:
                probe_idx, _, _ = choose_target_index(context)
                if probe_idx is not None:
                    battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=probe_idx)
                    if battle_click is not None:
                        attacking = False

        if attacking == False:
            if self._maybe_manual_auto_attack(context):
                return context

            closest_creature = ng_cave.get('closestCreature')
            if closest_creature and closest_creature.get('windowCoordinate'):
                # Original behavior:
                # - if there are players or ignorable creatures, use Alt+Click to avoid hotkey mis-targeting
                # - otherwise, use a hotkey (default space)
                players = game_window.get('players') or []
                has_players = len(players) > 0
                has_ignorable = bool(ng_targeting.get('hasIgnorableCreatures', False))
                if has_players or has_ignorable:
                    self._with_modifier_click(
                        closest_creature['windowCoordinate'],
                        modifier=get_str(
                            context,
                            'ng_runtime.attack_safe_click_modifier',
                            env_var='FENRIL_ATTACK_SAFE_CLICK_MODIFIER',
                            default='alt',
                            prefer_env=True,
                        ),
                        button=get_str(
                            context,
                            'ng_runtime.attack_click_button',
                            env_var='FENRIL_ATTACK_CLICK_BUTTON',
                            default='left',
                            prefer_env=True,
                        ),
                        context=context,
                        click_at_cursor=False,
                    )
                    if isinstance(context.get('ng_debug'), dict):
                        context['ng_debug']['last_tick_reason'] = 'attack click: closestCreature (safe)'
                    return context

                hotkey = get_str(
                    context,
                    'ng_runtime.attack_hotkey',
                    env_var='FENRIL_ATTACK_HOTKEY',
                    default='space',
                    prefer_env=True,
                ).strip().lower() or 'space'
                if get_bool(context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True):
                    log_throttled('input.attack.hotkey', 'info', f"input: attack hotkey={hotkey!r}", 1.0)
                keyboard.press(hotkey)
                if isinstance(context.get('ng_debug'), dict):
                    context['ng_debug']['last_tick_reason'] = f'attack hotkey: {hotkey}'
                return context

            # Fallback: click the first creature in battle list, if we can locate it.
            target_idx: int | None = None
            name: str | None = None
            reason: str = 'n/a'
            if battle_click is None and context.get('ng_screenshot') is not None:
                target_idx, name, reason = choose_target_index(context)
                if target_idx is not None:
                    battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=target_idx)
            if battle_click is not None:
                # Battle list clicks tend to work without Ctrl, and holding Ctrl can
                # open menus / behave unexpectedly depending on Tibia settings.
                self._with_modifier_click(
                    battle_click,
                    modifier=get_str(
                        context,
                        'ng_runtime.battlelist_attack_click_modifier',
                        env_var='FENRIL_BATTLELIST_ATTACK_CLICK_MODIFIER',
                        default='none',
                        prefer_env=True,
                    ),
                    button=get_str(
                        context,
                        'ng_runtime.battlelist_attack_click_button',
                        env_var='FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON',
                        default='left',
                        prefer_env=True,
                    ),
                    context=context,
                    click_at_cursor=get_bool(
                        context,
                        'ng_runtime.battlelist_click_at_cursor',
                        env_var='FENRIL_BATTLELIST_CLICK_AT_CURSOR',
                        default=False,
                        prefer_env=True,
                    ),
                )
                if isinstance(context.get('ng_debug'), dict):
                    # Extra structured diagnostics (useful when selection changes by name).
                    context['ng_debug']['battleList_target_index'] = int(target_idx) if target_idx is not None else -1
                    context['ng_debug']['battleList_target_name'] = name or ''
                    context['ng_debug']['battleList_target_reason'] = reason
                    context['ng_debug']['last_tick_reason'] = f'attack click: battleList[{target_idx if target_idx is not None else "?"}]'
                return context

            # If battle list targeting is enabled but we have no valid battle list entries
            # AND we also have no on-screen closestCreature, do not spam the attack hotkey.
            if (
                get_bool(context, 'ng_runtime.attack_from_battlelist', env_var='FENRIL_ATTACK_FROM_BATTLELIST', default=False)
                and ng_cave.get('targetCreature') is None
                and ng_cave.get('closestCreature') is None
                and (context.get('ng_battleList', {}).get('creatures') is None or len(context.get('ng_battleList', {}).get('creatures')) == 0)
            ):
                if isinstance(context.get('ng_debug'), dict):
                    context['ng_debug']['last_tick_reason'] = 'no valid targets (battle list empty)'
                return context

            # If we have no target and nothing to click, do NOT spam attack hotkeys.
            # (This is a common cause of "se queda atacando" when detection is empty.)
            if closest_creature is None and ng_cave.get('targetCreature') is None:
                if isinstance(context.get('ng_debug'), dict):
                    context['ng_debug']['last_tick_reason'] = 'idle (no target to attack)'
                return context

            # Last resort: send a hotkey (user-configurable).
            hotkey = get_str(
                context,
                'ng_runtime.attack_hotkey',
                env_var='FENRIL_ATTACK_HOTKEY',
                default='space',
                prefer_env=True,
            ).strip().lower() or 'space'
            if get_bool(context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False, prefer_env=True):
                log_throttled('input.attack.hotkey', 'info', f"input: attack hotkey={hotkey!r}", 1.0)
            keyboard.press(hotkey)
            if isinstance(context.get('ng_debug'), dict):
                context['ng_debug']['last_tick_reason'] = f'attack hotkey: {hotkey}'

        return context