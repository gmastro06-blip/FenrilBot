# TODO: add types
# TODO: add unit tests
from typing import Any, Dict

from src.utils.runtime_settings import get_bool


def loadContextFromConfig(config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    context['window_title'] = config.get('window_title')
    context['ng_backpacks'] = config['ng_backpacks'].copy()
    context['general_hotkeys'] = config['general_hotkeys'].copy()
    context['auto_hur'] = config['auto_hur'].copy()
    context['alert'] = config['alert'].copy()
    context['clear_stats'] = config['clear_stats'].copy()
    # Manual auto-attack (UI-controlled). Keep optional for older profiles.
    manual_defaults = {
        'enabled': False,
        'method': 'hotkey',
        'hotkey': 'pageup',
        'interval_s': 0.70,
        'only_when_not_attacking': False,
        'key_repeat': 1,
        'pre_delay_s': 0.02,
        'click_modifier': 'none',
        'click_button': 'left',
        'focus_before': False,
        'focus_after_s': 0.05,
    }
    manual_cfg = config.get('manual_auto_attack')
    if not isinstance(manual_cfg, dict):
        manual_cfg = {}
    context['manual_auto_attack'] = {**manual_defaults, **manual_cfg}

    # Runtime feature flags (prefer config, allow env var fallback in code).
    # Keeping these in profile avoids having to export env vars every time.
    runtime_defaults = {
        'attack_from_battlelist': False,
        'targeting_diag': False,
        'window_diag': False,
        'dump_task_on_timeout': False,
        'status_log_interval_s': 2.0,
        'loot_modifier': 'shift',
        'attack_only': False,
        'allow_attack_without_coord': False,
        'warn_on_window_miss': False,
        'action_window_title': '',
        'capture_window_title': '',
        'start_paused': True,
        # Diagnostics / logging
        'input_diag': False,
        'safe_log': False,
        'console_log': True,
        'log_level': 'info',
        # Capture / monitor
        'output_idx': 1,
        'auto_output_idx': True,
        # Capture stability / dxcam recovery
        'mss_fallback_on_none': False,
        'mss_fallback': False,
        'black_dark_pixel_threshold': 8,
        'black_dark_fraction_threshold': 0.98,
        'black_std_threshold': 2.0,
        'black_mean_threshold': 10.0,
        'black_mean_force_threshold': 3.0,
        'dxcam_retry_on_hard_black': True,
        'black_frame_threshold': 8,
        'same_frame_threshold': 300,
        'dxcam_recover_on_stale': True,
        'dxcam_recover_on_black': True,
        'log_dxcam_recovery': True,
        # Screenshot middleware diagnostics (black capture dumps)
        'diag_black_dump_threshold': 12,
        'dump_black_capture': False,
        'dump_black_capture_min_interval_s': 60.0,
        # Arduino input backend
        'arduino_port': 'COM33',
        'disable_arduino': False,
        'disable_arduino_clicks': False,
        # Radar / battle list diagnostics & recovery
        'radar_use_previous_on_miss': True,
        'radar_use_previous_max_ticks': 3,
        'dump_radar_on_fail': False,
        'dump_radar_min_interval_s': 60.0,
        'reset_locator_cache_threshold': 10,
        'diag_radar_missing_threshold': 30,
        'diag_arrows_missing_threshold': 30,
        'dump_radar_persistent': False,
        'dump_radar_persistent_min_interval_s': 120.0,
        'warn_on_battlelist_empty': True,
        'dump_battlelist_on_empty': False,
        'dump_battlelist_min_interval_s': 120.0,
        # Task timeouts (seconds)
        'task_timeouts': {
            'buyItem': 25.0,
            'dragItems': 25.0,
            'dragItemsToFloor': 25.0,
            'dropBackpackIntoStash': 20.0,
            'goToFreeDepot': 120.0,
            'openBackpack': 12.0,
            'openDepot': 10.0,
            'openLocker': 12.0,
            'scrollToItem': 20.0,
        },
        # Locator tunables (template matching confidence/scales)
        'radar_tools_confidence': 0.80,
        'radar_tools_multiscale': True,
        'radar_tools_min_scale': 0.80,
        'radar_tools_max_scale': 1.20,
        'radar_tools_scale_steps': 9,
        'battlelist_icon_confidence': 0.85,
        'battlelist_icon_min_scale': 0.70,
        'battlelist_icon_max_scale': 1.30,
        'battlelist_icon_scale_steps': 13,
        'battlelist_bottombar_confidence': 0.85,
        'battlelist_bottombar_min_scale': 0.70,
        'battlelist_bottombar_max_scale': 1.30,
        'battlelist_bottombar_scale_steps': 13,
        'battlelist_click_x_offset': 60,
        # UI-configured defaults
        'depot_open_button': 'right',
        # Attack input defaults (used by clickInClosestCreature)
        'attack_hotkey': 'space',
        'attack_click_button': 'left',
        'attack_safe_click_modifier': 'alt',
        'battlelist_attack_click_modifier': 'none',
        'battlelist_attack_click_button': 'left',
        'battlelist_click_at_cursor': False,
        'block_right_click_attack': False,
        'attack_click_pre_delay_s': 0.06,
    }
    runtime_cfg = config.get('ng_runtime')
    if not isinstance(runtime_cfg, dict):
        runtime_cfg = {}
    context['ng_runtime'] = {**runtime_defaults, **runtime_cfg}

    # Startup pause behavior: prefer profile config; allow env override for supervised/headless runs.
    context['ng_pause'] = get_bool(
        context,
        'ng_runtime.start_paused',
        env_var='FENRIL_START_PAUSED',
        default=True,
        prefer_env=True,
    )
    context['ignorable_creatures'] = config['ignorable_creatures'].copy()
    context['ng_cave']['enabled'] = config['ng_cave']['enabled']
    context['ng_cave']['runToCreatures'] = config['ng_cave']['runToCreatures']

    # Optional overrides for headless/supervised runs.
    context['ng_cave']['enabled'] = get_bool(
        context,
        'ng_cave.enabled',
        env_var='FENRIL_CAVEBOT_ENABLED',
        default=bool(context['ng_cave']['enabled']),
        prefer_env=True,
    )
    context['ng_cave']['runToCreatures'] = get_bool(
        context,
        'ng_cave.runToCreatures',
        env_var='FENRIL_RUN_TO_CREATURES',
        default=bool(context['ng_cave']['runToCreatures']),
        prefer_env=True,
    )
    context['ng_cave']['waypoints']['items'] = config['ng_cave']['waypoints']['items'].copy()
    context['ng_comboSpells']['enabled'] = config['ng_comboSpells']['enabled']
    context['ng_comboSpells']['items'] = []
    for comboSpellsItem in config['ng_comboSpells']['items']:
        comboSpellsItem['currentSpellIndex'] = 0
        context['ng_comboSpells']['items'].append(comboSpellsItem)
    context['healing'] = config['healing'].copy()
    return context

def loadNgCfgs(config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    context['ng_backpacks'] = config['ng_backpacks'].copy()
    context['general_hotkeys'] = config['general_hotkeys'].copy()
    context['auto_hur'] = config['auto_hur'].copy()
    context['alert'] = config['alert'].copy()
    context['clear_stats'] = config['clear_stats'].copy()
    manual_defaults = {
        'enabled': False,
        'method': 'hotkey',
        'hotkey': 'pageup',
        'interval_s': 0.70,
        'only_when_not_attacking': False,
        'key_repeat': 1,
        'pre_delay_s': 0.02,
        'click_modifier': 'none',
        'click_button': 'left',
        'focus_before': False,
        'focus_after_s': 0.05,
    }
    manual_cfg = config.get('manual_auto_attack')
    if not isinstance(manual_cfg, dict):
        manual_cfg = {}
    context['manual_auto_attack'] = {**manual_defaults, **manual_cfg}

    runtime_defaults = {
        'attack_from_battlelist': False,
        'targeting_diag': False,
        'window_diag': False,
        'dump_task_on_timeout': False,
        'status_log_interval_s': 2.0,
        'loot_modifier': 'shift',
        'attack_only': False,
        'allow_attack_without_coord': False,
        'warn_on_window_miss': False,
        'action_window_title': '',
        'capture_window_title': '',
        'start_paused': True,
        'input_diag': False,
        'safe_log': False,
        'console_log': True,
        'log_level': 'info',
        'output_idx': 1,
        'auto_output_idx': True,
        'mss_fallback_on_none': False,
        'mss_fallback': False,
        'black_dark_pixel_threshold': 8,
        'black_dark_fraction_threshold': 0.98,
        'black_std_threshold': 2.0,
        'black_mean_threshold': 10.0,
        'black_mean_force_threshold': 3.0,
        'dxcam_retry_on_hard_black': True,
        'black_frame_threshold': 8,
        'same_frame_threshold': 300,
        'dxcam_recover_on_stale': True,
        'dxcam_recover_on_black': True,
        'log_dxcam_recovery': True,
        'diag_black_dump_threshold': 12,
        'dump_black_capture': False,
        'dump_black_capture_min_interval_s': 60.0,
        'arduino_port': 'COM33',
        'disable_arduino': False,
        'disable_arduino_clicks': False,
        'radar_use_previous_on_miss': True,
        'radar_use_previous_max_ticks': 3,
        'dump_radar_on_fail': False,
        'dump_radar_min_interval_s': 60.0,
        # Attack input defaults (used by clickInClosestCreature)
        'attack_hotkey': 'space',
        'attack_click_button': 'left',
        'attack_safe_click_modifier': 'alt',
        'battlelist_attack_click_modifier': 'none',
        'battlelist_attack_click_button': 'left',
        'battlelist_click_at_cursor': False,
        'block_right_click_attack': False,
        'attack_click_pre_delay_s': 0.06,
        'reset_locator_cache_threshold': 10,
        'diag_radar_missing_threshold': 30,
        'diag_arrows_missing_threshold': 30,
        'dump_radar_persistent': False,
        'dump_radar_persistent_min_interval_s': 120.0,
        'warn_on_battlelist_empty': True,
        'dump_battlelist_on_empty': False,
        'dump_battlelist_min_interval_s': 120.0,
        'task_timeouts': {
            'buyItem': 25.0,
            'dragItems': 25.0,
            'dragItemsToFloor': 25.0,
            'dropBackpackIntoStash': 20.0,
            'goToFreeDepot': 120.0,
            'openBackpack': 12.0,
            'openDepot': 10.0,
            'openLocker': 12.0,
            'scrollToItem': 20.0,
        },
        'radar_tools_confidence': 0.80,
        'radar_tools_multiscale': True,
        'radar_tools_min_scale': 0.80,
        'radar_tools_max_scale': 1.20,
        'radar_tools_scale_steps': 9,
        'battlelist_icon_confidence': 0.85,
        'battlelist_icon_min_scale': 0.70,
        'battlelist_icon_max_scale': 1.30,
        'battlelist_icon_scale_steps': 13,
        'battlelist_bottombar_confidence': 0.85,
        'battlelist_bottombar_min_scale': 0.70,
        'battlelist_bottombar_max_scale': 1.30,
        'battlelist_bottombar_scale_steps': 13,
        'battlelist_click_x_offset': 60,
        'depot_open_button': 'right',
    }
    runtime_cfg = config.get('ng_runtime')
    if not isinstance(runtime_cfg, dict):
        runtime_cfg = {}
    context['ng_runtime'] = {**runtime_defaults, **runtime_cfg}
    try:
        context['ng_pause'] = bool(context.get('ng_runtime', {}).get('start_paused', True))
    except Exception:
        context['ng_pause'] = True
    context['ng_comboSpells']['enabled'] = config['ng_comboSpells']['enabled']
    context['ng_comboSpells']['items'] = []
    for comboSpellsItem in config['ng_comboSpells']['items']:
        comboSpellsItem['currentSpellIndex'] = 0
        context['ng_comboSpells']['items'].append(comboSpellsItem)
    context['healing'] = config['healing'].copy()
    return context
