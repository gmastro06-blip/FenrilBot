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
    context['manual_auto_attack'] = (config.get('manual_auto_attack') or {
        'enabled': False,
        'method': 'hotkey',
        'hotkey': 'pageup',
        'interval_s': 0.70,
    }).copy()
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
    context['manual_auto_attack'] = (config.get('manual_auto_attack') or {
        'enabled': False,
        'method': 'hotkey',
        'hotkey': 'pageup',
        'interval_s': 0.70,
    }).copy()
    context['ng_comboSpells']['enabled'] = config['ng_comboSpells']['enabled']
    context['ng_comboSpells']['items'] = []
    for comboSpellsItem in config['ng_comboSpells']['items']:
        comboSpellsItem['currentSpellIndex'] = 0
        context['ng_comboSpells']['items'].append(comboSpellsItem)
    context['healing'] = config['healing'].copy()
    return context
