import os
import time

import src.utils.keyboard as keyboard
import src.utils.mouse as mouse
from src.gameplay.typings import Context
from .common.base import BaseTask
from src.repositories.battleList import extractors as battlelist_extractors
from src.shared.typings import XYCoordinate
from src.utils.console_log import log_throttled
from src.utils.runtime_settings import get_bool

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

        manual_cfg = context.get('manual_auto_attack') if isinstance(context, dict) else None
        cfg_enabled = False
        if isinstance(manual_cfg, dict):
            cfg_enabled = bool(manual_cfg.get('enabled', False))

        env_enabled = os.getenv('FENRIL_MANUAL_AUTO_ATTACK', '0') in {'1', 'true', 'True'}
        if not (cfg_enabled or env_enabled):
            return False

        # By default, manual auto-attack runs regardless of current attacking state
        # (useful for "next target" cycling). You can restrict it if desired.
        only_when_not_attacking = False
        if isinstance(manual_cfg, dict) and manual_cfg.get('only_when_not_attacking') is not None:
            only_when_not_attacking = bool(manual_cfg.get('only_when_not_attacking'))
        else:
            only_when_not_attacking = os.getenv('FENRIL_MANUAL_AUTO_ATTACK_ONLY_WHEN_NOT_ATTACKING', '0') in {'1', 'true', 'True'}
        attacking = bool(context.get('ng_cave', {}).get('isAttackingSomeCreature', False))
        if only_when_not_attacking and attacking:
            return False

        interval_s = None
        if isinstance(manual_cfg, dict):
            try:
                raw_interval = manual_cfg.get('interval_s')
                if raw_interval is not None:
                    interval_s = float(raw_interval)
            except Exception:
                interval_s = None
        if interval_s is None:
            try:
                interval_s = float(os.getenv('FENRIL_MANUAL_AUTO_ATTACK_INTERVAL_S', '0.70'))
            except Exception:
                interval_s = 0.70

        now = time.time()
        if (now - self._last_manual_attack_ts) < interval_s:
            return True
        self._last_manual_attack_ts = now

        method = None
        if isinstance(manual_cfg, dict):
            try:
                method = str(manual_cfg.get('method', '')).strip().lower()
            except Exception:
                method = None
        if not method:
            method = os.getenv('FENRIL_MANUAL_AUTO_ATTACK_METHOD', 'hotkey').strip().lower()

        if method in {'click', 'cursor', 'cursor_click'}:
            # Click at current cursor position.
            # NOTE: this intentionally does not move the mouse.
            modifier = None
            button = None
            if isinstance(manual_cfg, dict):
                try:
                    modifier = str(manual_cfg.get('click_modifier', '')).strip().lower() or None
                except Exception:
                    modifier = None
                try:
                    button = str(manual_cfg.get('click_button', '')).strip().lower() or None
                except Exception:
                    button = None
            if not modifier:
                modifier = os.getenv('FENRIL_MANUAL_AUTO_ATTACK_CLICK_MODIFIER', 'none')
            if not button:
                button = os.getenv('FENRIL_MANUAL_AUTO_ATTACK_CLICK_BUTTON', 'left')
            self._with_modifier_click(
                (0, 0),
                modifier=modifier,
                button=button,
                context=context,
                click_at_cursor=True,
            )
            if isinstance(context.get('ng_debug'), dict):
                context['ng_debug']['last_tick_reason'] = 'manual auto-attack: cursor click'
            return True

        # Default: hotkey
        hotkey = None
        if isinstance(manual_cfg, dict):
            try:
                hotkey = str(manual_cfg.get('hotkey', '')).strip().lower()
            except Exception:
                hotkey = None
        if not hotkey:
            hotkey = os.getenv('FENRIL_MANUAL_AUTO_ATTACK_HOTKEY', '').strip().lower()
        if not hotkey:
            # Default to Tibia next-target hotkey for manual cycling.
            hotkey = os.getenv('FENRIL_ATTACK_HOTKEY', 'pageup').strip().lower()

        focus_enabled = False
        if isinstance(manual_cfg, dict) and manual_cfg.get('focus_before') is not None:
            focus_enabled = bool(manual_cfg.get('focus_before'))
        else:
            focus_raw = os.getenv('FENRIL_FOCUS_ACTION_WINDOW_BEFORE_MANUAL_HOTKEY')
            if focus_raw is None:
                focus_raw = os.getenv('FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK', '0')
            focus_enabled = focus_raw not in {'0', 'false', 'False'}
        if focus_enabled:
            self._focus_action_window(context)
            try:
                pre_delay_s = None
                if isinstance(manual_cfg, dict) and manual_cfg.get('pre_delay_s') is not None:
                    try:
                        raw_pre = manual_cfg.get('pre_delay_s')
                        if raw_pre is not None:
                            pre_delay_s = float(raw_pre)
                    except Exception:
                        pre_delay_s = None
                if pre_delay_s is None:
                    pre_delay_s = float(os.getenv('FENRIL_MANUAL_AUTO_ATTACK_PRE_DELAY_S', '0.02'))
                time.sleep(pre_delay_s)
            except Exception:
                pass

        # Optional extra reliability: repeat the key press a few times.
        repeats = None
        if isinstance(manual_cfg, dict) and manual_cfg.get('key_repeat') is not None:
            try:
                raw_repeats = manual_cfg.get('key_repeat')
                if raw_repeats is not None:
                    repeats = int(raw_repeats)
            except Exception:
                repeats = None
        if repeats is None:
            try:
                repeats = int(os.getenv('FENRIL_MANUAL_AUTO_ATTACK_KEY_REPEAT', '1'))
            except Exception:
                repeats = 1
        if repeats < 1:
            repeats = 1
        if repeats > 3:
            repeats = 3
        if os.getenv('FENRIL_INPUT_DIAG', '0') in {'1', 'true', 'True'}:
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
        manual_cfg = context.get('manual_auto_attack') if isinstance(context, dict) else None
        if isinstance(manual_cfg, dict) and manual_cfg.get('focus_before') is not None:
            if not bool(manual_cfg.get('focus_before')):
                return False
        else:
            if os.getenv('FENRIL_FOCUS_ACTION_WINDOW_BEFORE_ATTACK_CLICK', '0') in {'0', 'false', 'False'}:
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
            delay_s = None
            if isinstance(manual_cfg, dict) and manual_cfg.get('focus_after_s') is not None:
                try:
                    raw_focus_after = manual_cfg.get('focus_after_s')
                    if raw_focus_after is not None:
                        delay_s = float(raw_focus_after)
                except Exception:
                    delay_s = None
            if delay_s is None:
                try:
                    delay_s = float(os.getenv('FENRIL_FOCUS_AFTER_S', '0.05'))
                except Exception:
                    delay_s = 0.05
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
    ) -> None:
        modifier = modifier.strip().lower()
        button = button.strip().lower()

        if button not in {'left', 'right'}:
            button = 'left'

        # Safety: allow users to completely disable right-click during targeting.
        # This affects ONLY this task (attack clicks), not waypoint/utility tasks.
        if os.getenv('FENRIL_BLOCK_RIGHT_CLICK_ATTACK', '0') in {'1', 'true', 'True'}:
            button = 'left'

        focused = self._focus_action_window(context)

        if os.getenv('FENRIL_INPUT_DIAG', '0') in {'1', 'true', 'True'}:
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
            try:
                mouse.moveTo(coord)
                time.sleep(float(os.getenv('FENRIL_ATTACK_CLICK_PRE_DELAY_S', '0.06')))
            except Exception:
                pass

        if modifier in {'none', 'no', '0', ''}:
            if button == 'right':
                mouse.rightClick(None if click_at_cursor else coord)
            else:
                mouse.leftClick(None if click_at_cursor else coord)

            if os.getenv('FENRIL_INPUT_DIAG', '0') in {'1', 'true', 'True'}:
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

        if os.getenv('FENRIL_INPUT_DIAG', '0') in {'1', 'true', 'True'}:
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
                # Even if parsing returns 0 entries, we may still have a locatable battle list.
                # Keep clicking until an on-screen targetCreature is acquired.
                if context.get('ng_screenshot') is not None:
                    battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=0)
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
                battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=0)
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
                        modifier=os.getenv('FENRIL_ATTACK_SAFE_CLICK_MODIFIER', 'alt'),
                        button=os.getenv('FENRIL_ATTACK_CLICK_BUTTON', 'left'),
                        context=context,
                        click_at_cursor=False,
                    )
                    if isinstance(context.get('ng_debug'), dict):
                        context['ng_debug']['last_tick_reason'] = 'attack click: closestCreature (safe)'
                    return context

                hotkey = os.getenv('FENRIL_ATTACK_HOTKEY', 'space')
                if os.getenv('FENRIL_INPUT_DIAG', '0') in {'1', 'true', 'True'}:
                    log_throttled('input.attack.hotkey', 'info', f"input: attack hotkey={hotkey!r}", 1.0)
                keyboard.press(hotkey)
                if isinstance(context.get('ng_debug'), dict):
                    context['ng_debug']['last_tick_reason'] = f'attack hotkey: {hotkey}'
                return context

            # Fallback: click the first creature in battle list, if we can locate it.
            if battle_click is None and context.get('ng_screenshot') is not None:
                battle_click = battlelist_extractors.getCreatureClickCoordinate(context['ng_screenshot'], index=0)
            if battle_click is not None:
                # Battle list clicks tend to work without Ctrl, and holding Ctrl can
                # open menus / behave unexpectedly depending on Tibia settings.
                self._with_modifier_click(
                    battle_click,
                    modifier=os.getenv('FENRIL_BATTLELIST_ATTACK_CLICK_MODIFIER', 'none'),
                    button=os.getenv('FENRIL_BATTLELIST_ATTACK_CLICK_BUTTON', 'left'),
                    context=context,
                    click_at_cursor=os.getenv('FENRIL_BATTLELIST_CLICK_AT_CURSOR', '0') in {'1', 'true', 'True'},
                )
                if isinstance(context.get('ng_debug'), dict):
                    context['ng_debug']['last_tick_reason'] = 'attack click: battleList[0]'
                return context

            # Last resort: send a hotkey (user-configurable).
            hotkey = os.getenv('FENRIL_ATTACK_HOTKEY', 'space')
            if os.getenv('FENRIL_INPUT_DIAG', '0') in {'1', 'true', 'True'}:
                log_throttled('input.attack.hotkey', 'info', f"input: attack hotkey={hotkey!r}", 1.0)
            keyboard.press(hotkey)
            if isinstance(context.get('ng_debug'), dict):
                context['ng_debug']['last_tick_reason'] = f'attack hotkey: {hotkey}'

        return context