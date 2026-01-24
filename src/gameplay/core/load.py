# TODO: add types
# TODO: add unit tests
import os
from typing import Any, Dict


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
    }
    runtime_cfg = config.get('ng_runtime')
    if not isinstance(runtime_cfg, dict):
        runtime_cfg = {}
    context['ng_runtime'] = {**runtime_defaults, **runtime_cfg}

    # Startup pause behavior: prefer profile config; allow env override for supervised/headless runs.
    try:
        context['ng_pause'] = bool(context.get('ng_runtime', {}).get('start_paused', True))
    except Exception:
        context['ng_pause'] = True
    start_paused_raw = os.getenv('FENRIL_START_PAUSED')
    if start_paused_raw is not None:
        context['ng_pause'] = start_paused_raw.strip().lower() in {'1', 'true', 'yes', 'y'}
    context['ignorable_creatures'] = config['ignorable_creatures'].copy()
    context['ng_cave']['enabled'] = config['ng_cave']['enabled']
    context['ng_cave']['runToCreatures'] = config['ng_cave']['runToCreatures']

    # Optional overrides for headless/supervised runs.
    # Accept either 0/1 or true/false.
    cave_enabled_raw = os.getenv('FENRIL_CAVEBOT_ENABLED')
    if cave_enabled_raw is not None:
        context['ng_cave']['enabled'] = cave_enabled_raw.strip().lower() in {'1', 'true', 'yes', 'y'}
    run_to_raw = os.getenv('FENRIL_RUN_TO_CREATURES')
    if run_to_raw is not None:
        context['ng_cave']['runToCreatures'] = run_to_raw.strip().lower() in {'1', 'true', 'yes', 'y'}
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
