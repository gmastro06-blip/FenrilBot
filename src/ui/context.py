from os.path import exists
import time
from typing import Any, Callable, Dict, List, Optional, cast

from tinydb import Query, TinyDB
from tkinter import messagebox
import pygetwindow as gw
from src.gameplay.core.load import loadContextFromConfig, loadNgCfgs
from src.repositories.chat.core import resetOldList
# from src.utils.core import getScreenshot
from src.utils.console_log import log
from src.utils.console_log import configure_console_log
from src.utils.core import configure_capture, setScreenshotOutputIdx
from src.utils.ino import configure_arduino
from src.utils.mouse import configure_mouse
from src.utils.runtime_settings import get_bool, get_float, get_int, get_str
from src.utils.safety import configure_safe_log
from src.repositories.radar.locators import configure_radar_locators
from src.repositories.battleList.locators import configure_battlelist_locators
from src.repositories.battleList.extractors import configure_battlelist_extractors


class Context:
    filePath: str = 'file.json'

    def __init__(self, context: Dict[str, Any]) -> None:
        shouldInsertProfile = not exists(self.filePath)
        self.db = TinyDB(self.filePath)
        if shouldInsertProfile:
            self.insertProfile()
        self.enabledProfile = self.getEnabledProfile()
        load_context = cast(Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]], loadContextFromConfig)
        self.context = load_context(
            self.enabledProfile['config'], context)

        # Apply runtime configuration to global helpers/backends.
        try:
            output_idx = get_int(self.context, 'ng_runtime.output_idx', env_var='FENRIL_OUTPUT_IDX', default=1)
            if output_idx < 1:
                output_idx = 1
            setScreenshotOutputIdx(output_idx)
        except Exception:
            pass

        try:
            configure_capture(
                mss_fallback_on_none=get_bool(self.context, 'ng_runtime.mss_fallback_on_none', env_var='FENRIL_MSS_FALLBACK_ON_NONE', default=False),
                mss_fallback=get_bool(self.context, 'ng_runtime.mss_fallback', env_var='FENRIL_MSS_FALLBACK', default=False),
                black_dark_pixel_threshold=get_int(self.context, 'ng_runtime.black_dark_pixel_threshold', env_var='FENRIL_BLACK_DARK_PIXEL_THRESHOLD', default=8),
                black_dark_fraction_threshold=get_float(self.context, 'ng_runtime.black_dark_fraction_threshold', env_var='FENRIL_BLACK_DARK_FRACTION_THRESHOLD', default=0.98),
                black_std_threshold=get_float(self.context, 'ng_runtime.black_std_threshold', env_var='FENRIL_BLACK_STD_THRESHOLD', default=1.0),
                black_mean_threshold=get_float(self.context, 'ng_runtime.black_mean_threshold', env_var='FENRIL_BLACK_MEAN_THRESHOLD', default=2.0),
                black_mean_force_threshold=get_float(self.context, 'ng_runtime.black_mean_force_threshold', env_var='FENRIL_BLACK_MEAN_FORCE_THRESHOLD', default=2.0),
                dxcam_retry_on_hard_black=get_bool(self.context, 'ng_runtime.dxcam_retry_on_hard_black', env_var='FENRIL_DXCAM_RETRY_ON_HARD_BLACK', default=True),
                black_frame_threshold=get_int(self.context, 'ng_runtime.black_frame_threshold', env_var='FENRIL_BLACK_FRAME_THRESHOLD', default=8),
                same_frame_threshold=get_int(self.context, 'ng_runtime.same_frame_threshold', env_var='FENRIL_SAME_FRAME_THRESHOLD', default=30),
                dxcam_recover_on_stale=get_bool(self.context, 'ng_runtime.dxcam_recover_on_stale', env_var='FENRIL_DXCAM_RECOVER_ON_STALE', default=True),
                dxcam_recover_on_black=get_bool(self.context, 'ng_runtime.dxcam_recover_on_black', env_var='FENRIL_DXCAM_RECOVER_ON_BLACK', default=True),
                log_dxcam_recovery=get_bool(self.context, 'ng_runtime.log_dxcam_recovery', env_var='FENRIL_LOG_DXCAM_RECOVERY', default=True),
            )
        except Exception:
            pass

        try:
            configure_console_log(
                level=get_str(self.context, 'ng_runtime.log_level', env_var='FENRIL_LOG_LEVEL', default='info'),
                enabled=get_bool(self.context, 'ng_runtime.console_log', env_var='FENRIL_CONSOLE_LOG', default=True),
            )
        except Exception:
            pass

        try:
            configure_safe_log(enabled=get_bool(self.context, 'ng_runtime.safe_log', env_var='FENRIL_SAFE_LOG', default=False))
        except Exception:
            pass

        try:
            configure_arduino(
                port=get_str(self.context, 'ng_runtime.arduino_port', env_var='FENRIL_ARDUINO_PORT', default='COM33'),
                disable_arduino=get_bool(self.context, 'ng_runtime.disable_arduino', env_var='FENRIL_DISABLE_ARDUINO', default=False),
                disable_clicks=get_bool(self.context, 'ng_runtime.disable_arduino_clicks', env_var='FENRIL_DISABLE_ARDUINO_CLICKS', default=False),
            )
        except Exception:
            pass

        try:
            configure_mouse(
                input_diag=get_bool(self.context, 'ng_runtime.input_diag', env_var='FENRIL_INPUT_DIAG', default=False),
                disable_arduino_clicks=get_bool(self.context, 'ng_runtime.disable_arduino_clicks', env_var='FENRIL_DISABLE_ARDUINO_CLICKS', default=False),
            )
        except Exception:
            pass

        # Locator tunables (scaling/confidence) - configure once at startup.
        try:
            configure_radar_locators(
                tools_confidence=get_float(self.context, 'ng_runtime.radar_tools_confidence', env_var='FENRIL_RADAR_TOOLS_CONFIDENCE', default=0.80),
                tools_multiscale=get_bool(self.context, 'ng_runtime.radar_tools_multiscale', env_var='FENRIL_RADAR_TOOLS_MULTISCALE', default=True),
                tools_min_scale=get_float(self.context, 'ng_runtime.radar_tools_min_scale', env_var='FENRIL_RADAR_TOOLS_MIN_SCALE', default=0.80),
                tools_max_scale=get_float(self.context, 'ng_runtime.radar_tools_max_scale', env_var='FENRIL_RADAR_TOOLS_MAX_SCALE', default=1.20),
                tools_scale_steps=get_int(self.context, 'ng_runtime.radar_tools_scale_steps', env_var='FENRIL_RADAR_TOOLS_SCALE_STEPS', default=9),
            )
        except Exception:
            pass

        try:
            configure_battlelist_locators(
                icon_confidence=get_float(self.context, 'ng_runtime.battlelist_icon_confidence', env_var='FENRIL_BATTLELIST_ICON_CONFIDENCE', default=0.85),
                icon_min_scale=get_float(self.context, 'ng_runtime.battlelist_icon_min_scale', env_var='FENRIL_BATTLELIST_ICON_MIN_SCALE', default=0.70),
                icon_max_scale=get_float(self.context, 'ng_runtime.battlelist_icon_max_scale', env_var='FENRIL_BATTLELIST_ICON_MAX_SCALE', default=1.30),
                icon_scale_steps=get_int(self.context, 'ng_runtime.battlelist_icon_scale_steps', env_var='FENRIL_BATTLELIST_ICON_SCALE_STEPS', default=13),
                bottom_confidence=get_float(self.context, 'ng_runtime.battlelist_bottombar_confidence', env_var='FENRIL_BATTLELIST_BOTTOMBAR_CONFIDENCE', default=0.85),
                bottom_min_scale=get_float(self.context, 'ng_runtime.battlelist_bottombar_min_scale', env_var='FENRIL_BATTLELIST_BOTTOMBAR_MIN_SCALE', default=0.70),
                bottom_max_scale=get_float(self.context, 'ng_runtime.battlelist_bottombar_max_scale', env_var='FENRIL_BATTLELIST_BOTTOMBAR_MAX_SCALE', default=1.30),
                bottom_scale_steps=get_int(self.context, 'ng_runtime.battlelist_bottombar_scale_steps', env_var='FENRIL_BATTLELIST_BOTTOMBAR_SCALE_STEPS', default=13),
            )
        except Exception:
            pass

        try:
            configure_battlelist_extractors(
                click_x_offset=get_int(self.context, 'ng_runtime.battlelist_click_x_offset', env_var='FENRIL_BATTLELIST_CLICK_X_OFFSET', default=80),
            )
        except Exception:
            pass
        window_title = self.enabledProfile['config'].get('window_title')
        if window_title:
            self.setWindowTitle(window_title, persist=False)

    def updateMainBackpack(self, backpack: str) -> None:
        # Asegurar que la estructura existe antes de acceder
        if 'ng_backpacks' not in self.context:
            self.context['ng_backpacks'] = {}
        if not isinstance(self.context['ng_backpacks'], dict):
            self.context['ng_backpacks'] = {}
        self.context['ng_backpacks']['main'] = backpack
        
        if not isinstance(self.enabledProfile.get('config'), dict):
            self.enabledProfile['config'] = {}
        if 'ng_backpacks' not in self.enabledProfile['config']:
            self.enabledProfile['config']['ng_backpacks'] = {}
        if not isinstance(self.enabledProfile['config']['ng_backpacks'], dict):
            self.enabledProfile['config']['ng_backpacks'] = {}
        self.enabledProfile['config']['ng_backpacks']['main'] = backpack
        self.db.update(self.enabledProfile)

    def insertProfile(self) -> None:
        self.db.insert({
            'enabled': True,
            'config': {
                'window_title': None,
                'ng_backpacks': {
                    'main': None,
                    'loot': None
                },
                'ng_cave': {
                    'enabled': False,
                    'runToCreatures': False,
                    'waypoints': {
                        'items': []
                    }
                },
                'ng_comboSpells': {
                    'enabled': False,
                    'items': []
                },
                'general_hotkeys': {
                    'shovel_hotkey': 'p',
                    'rope_hotkey': 'o'
                },
                'auto_hur': {
                    'enabled': False,
                    'hotkey': 't',
                    'spell': 'utani hur',
                    'pz': False
                },
                'alert': {
                    'enabled': False,
                    'cave': False,
                    'sayPlayer': False
                },
                'clear_stats': {
                    'poison': False,
                    'poison_hotkey': 'g'
                },
                'manual_auto_attack': {
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
                },
                'ng_runtime': {
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
                    'depot_open_button': 'left',
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
                    'black_std_threshold': 1.0,
                    'black_mean_threshold': 2.0,
                    'black_mean_force_threshold': 2.0,
                    'dxcam_retry_on_hard_black': True,
                    'black_frame_threshold': 8,
                    'same_frame_threshold': 30,
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
                },
                'ignorable_creatures': [],
                'healing': {
                    'highPriority': {
                        'healthFood': {
                            'enabled': False,
                            'hotkey': '3',
                            'hpPercentageLessThanOrEqual': 0,
                        },
                        'manaFood': {
                            'enabled': False,
                            'hotkey': '4',
                            'manaPercentageLessThanOrEqual': 0,
                        },
                        'swapRing': {
                            'enabled': False,
                            'tankRing': {
                                'hotkey': 'f11',
                                'hpPercentageLessThanOrEqual': 0,
                                'slot': 21
                            },
                            'mainRing': {
                                'hotkey': 'f12',
                                'hpPercentageGreaterThan': 0,
                                'slot': 22
                            },
                            'tankRingAlwaysEquipped': False
                        },
                        'swapAmulet': {
                            'enabled': False,
                            'tankAmulet': {
                                'hotkey': 'u',
                                'hpPercentageLessThanOrEqual': 0,
                                'slot': 23
                            },
                            'mainAmulet': {
                                'hotkey': 'i',
                                'hpPercentageGreaterThan': 0,
                                'slot': 24
                            },
                            'tankAmuletAlwaysEquipped': False
                        }
                    },
                    'potions': {
                        'firstHealthPotion': {
                            'enabled': False,
                            'hotkey': '1',
                            'slot': 1,
                            'hpPercentageLessThanOrEqual': 0,
                            'manaPercentageGreaterThanOrEqual': 0,
                        },
                        'firstManaPotion': {
                            'enabled': False,
                            'hotkey': '2',
                            'slot': 2,
                            'manaPercentageLessThanOrEqual': 0,
                        },
                    },
                    'spells': {
                        'criticalHealing': {
                            'enabled': False,
                            'hotkey': '5',
                            'hpPercentageLessThanOrEqual': 0,
                            'manaPercentageGreaterThanOrEqual': 0,
                            'spell': None
                        },
                        'lightHealing': {
                            'enabled': False,
                            'hotkey': '7',
                            'hpPercentageLessThanOrEqual': 0,
                            'manaPercentageGreaterThanOrEqual': 0,
                            'spell': None
                        },
                        'utura': {
                            'enabled': False,
                            'hotkey': '8',
                            'hpPercentageLessThanOrEqual': 0,
                            'manaPercentageGreaterThanOrEqual': 0,
                            'spell': None
                        },
                        'uturaGran': {
                            'enabled': False,
                            'hotkey': '9',
                            'hpPercentageLessThanOrEqual': 0,
                            'manaPercentageGreaterThanOrEqual': 0,
                            'spell': None
                        },
                    },
                    'eatFood': {
                        'enabled': False,
                        'hotkey': 'f',
                        'eatWhenFoodIslessOrEqual': 0,
                    }
                },
            }
        })

    def loadScript(self, script: List[Dict[str, Any]]) -> None:
        upgraded = script.copy()
        try:
            self._upgradeLegacyWaypointsInPlace(upgraded)
        except Exception:
            pass

        # Asegurar que la estructura ng_cave existe
        if 'ng_cave' not in self.context:
            self.context['ng_cave'] = {}
        if not isinstance(self.context['ng_cave'], dict):
            self.context['ng_cave'] = {}
        if 'waypoints' not in self.context['ng_cave']:
            self.context['ng_cave']['waypoints'] = {}
        if not isinstance(self.context['ng_cave']['waypoints'], dict):
            self.context['ng_cave']['waypoints'] = {}
        
        self.context['ng_cave']['waypoints']['items'] = upgraded
        
        if not isinstance(self.enabledProfile.get('config'), dict):
            self.enabledProfile['config'] = {}
        if 'ng_cave' not in self.enabledProfile['config']:
            self.enabledProfile['config']['ng_cave'] = {}
        if not isinstance(self.enabledProfile['config']['ng_cave'], dict):
            self.enabledProfile['config']['ng_cave'] = {}
        if 'waypoints' not in self.enabledProfile['config']['ng_cave']:
            self.enabledProfile['config']['ng_cave']['waypoints'] = {}
        if not isinstance(self.enabledProfile['config']['ng_cave']['waypoints'], dict):
            self.enabledProfile['config']['ng_cave']['waypoints'] = {}
        
        self.enabledProfile['config']['ng_cave']['waypoints']['items'] = upgraded
        self.db.update(self.enabledProfile)

    def _getLegacyRefillOptions(self) -> Optional[Dict[str, Any]]:
        try:
            ng_legacy = self.context.get('ng_legacy') if isinstance(self.context, dict) else None
            if isinstance(ng_legacy, dict) and isinstance(ng_legacy.get('refill_options'), dict):
                return cast(Dict[str, Any], ng_legacy.get('refill_options'))
        except Exception:
            pass
        try:
            prof_legacy = self.enabledProfile.get('config', {}).get('ng_legacy')
            if isinstance(prof_legacy, dict) and isinstance(prof_legacy.get('refill_options'), dict):
                return cast(Dict[str, Any], prof_legacy.get('refill_options'))
        except Exception:
            pass
        return None

    def _getLegacyRefillCheckerBase(self) -> Optional[Dict[str, Any]]:
        try:
            ng_legacy = self.context.get('ng_legacy') if isinstance(self.context, dict) else None
            if isinstance(ng_legacy, dict) and isinstance(ng_legacy.get('refill_checker_base'), dict):
                return cast(Dict[str, Any], ng_legacy.get('refill_checker_base'))
        except Exception:
            pass
        try:
            prof_legacy = self.enabledProfile.get('config', {}).get('ng_legacy')
            if isinstance(prof_legacy, dict) and isinstance(prof_legacy.get('refill_checker_base'), dict):
                return cast(Dict[str, Any], prof_legacy.get('refill_checker_base'))
        except Exception:
            pass
        return None

    def _upgradeLegacyWaypointsInPlace(self, waypoints: List[Dict[str, Any]]) -> bool:
        refill_options = self._getLegacyRefillOptions()
        refill_checker_base = self._getLegacyRefillCheckerBase()
        if not isinstance(refill_options, dict) and not isinstance(refill_checker_base, dict):
            return False

        changed = False

        def _find_next_label(start_index: int) -> Optional[str]:
            for nxt in waypoints[start_index + 1:]:
                if not isinstance(nxt, dict):
                    continue
                label = nxt.get('label')
                if isinstance(label, str) and label.strip():
                    return label.strip()
            return None

        for idx, wp in enumerate(waypoints):
            if not isinstance(wp, dict):
                continue
            opts_any = wp.get('options')
            opts: Dict[str, Any] = cast(Dict[str, Any], opts_any) if isinstance(opts_any, dict) else {}
            action = opts.get('action')
            if action == 'buy_potions' and isinstance(refill_options, dict):
                wp['type'] = 'refill'
                wp['ignore'] = False
                wp['options'] = refill_options
                changed = True

            if action == 'sell':
                wp['type'] = 'sellFlasks'
                wp['ignore'] = False
                if isinstance(opts, dict):
                    cleaned = dict(opts)
                    cleaned.pop('action', None)
                    wp['options'] = cleaned
                else:
                    wp['options'] = {}
                changed = True

            if action in {'check_supplies', 'check'} and isinstance(refill_checker_base, dict):
                next_label = _find_next_label(idx)
                if not next_label:
                    continue
                wp['type'] = 'refillChecker'
                wp['ignore'] = False
                merged = dict(refill_checker_base)
                merged['waypointLabelToRedirect'] = next_label
                wp['options'] = merged
                changed = True
        return changed

    def loadCfg(self, cfg: Dict[str, Any]) -> None:
        load_cfgs = cast(Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]], loadNgCfgs)
        self.context = load_cfgs(cfg, self.context)
        
        # Validación defensiva: usar .get() para prevenir KeyError
        if not isinstance(self.enabledProfile.get('config'), dict):
            self.enabledProfile['config'] = {}
        
        self.enabledProfile['config']['ng_backpacks'] = self.context.get('ng_backpacks', {})
        self.enabledProfile['config']['general_hotkeys'] = self.context.get('general_hotkeys', {})
        self.enabledProfile['config']['auto_hur'] = self.context.get('auto_hur', {})
        self.enabledProfile['config']['alert'] = self.context.get('alert', {})
        self.enabledProfile['config']['clear_stats'] = self.context.get('clear_stats', {})
        self.enabledProfile['config']['manual_auto_attack'] = self.context.get('manual_auto_attack', {})
        self.enabledProfile['config']['ng_runtime'] = self.context.get('ng_runtime', {})
        
        # Validar que ng_comboSpells existe
        ng_combo = self.context.get('ng_comboSpells', {})
        if not isinstance(ng_combo, dict):
            ng_combo = {'enabled': False, 'items': []}
        if 'ng_comboSpells' not in self.enabledProfile['config']:
            self.enabledProfile['config']['ng_comboSpells'] = {}
        
        self.enabledProfile['config']['ng_comboSpells']['enabled'] = ng_combo.get('enabled', False)
        self.enabledProfile['config']['ng_comboSpells']['items'] = []
        
        for comboSpellsItem in ng_combo.get('items', []):
            if isinstance(comboSpellsItem, dict):
                comboSpellsItem['currentSpellIndex'] = 0
                self.enabledProfile['config']['ng_comboSpells']['items'].append(comboSpellsItem)
        
        self.enabledProfile['config']['healing'] = self.context.get('healing', {})
        self.db.update(self.enabledProfile)

    def importLegacySetup(self, setup: Dict[str, Any]) -> None:
        """Import a legacy scripts-master setup_*.json into the current profile.

        Supported mappings:
        - `hunt_config.mana_name` + `hunt_config.take_mana` -> converts any waypoint with
          `options.action == 'buy_potions'` into a real `refill` waypoint (trade mode).
                - `hunt_config.mana_leave` + `hunt_config.cap_leave` -> converts any waypoint with
                    `options.action in {'check_supplies', 'check'}` into a real `refillChecker` waypoint.
        - `items[mana_name].hotkey` + healing mp rule -> updates `healing.potions.firstManaPotion`.
        - healing hp spell rule + `spells[spell]` -> updates `healing.spells.lightHealing`.
        - `persistent_actions: eat_food` -> updates `healing.eatFood` hotkey.
        """
        if not isinstance(setup, dict):
            return

        def _to_int(value: Any, default: int = 0) -> int:
            try:
                if value is None:
                    return default
                return int(value)
            except Exception:
                return default

        def _normalize_refill_item_name(name: str) -> str:
            key = name.strip().lower()
            mana_map = {
                'mana potion': 'Mana Potion',
                'strong mana potion': 'Strong Mana Potion',
                'great mana potion': 'Great Mana Potion',
                'ultimate mana potion': 'Ultimate Mana Potion',
            }
            health_map = {
                'small health potion': 'Small Health Potion',
                'health potion': 'Health Potion',
                'strong health potion': 'Strong Health Potion',
                'great health potion': 'Great Health Potion',
                'ultimate health potion': 'Ultimate Health Potion',
                'supreme health potion': 'Supreme Health Potion',
            }
            return mana_map.get(key) or health_map.get(key) or name

        hunt_cfg_any = setup.get('hunt_config')
        hunt_cfg: Dict[str, Any] = cast(Dict[str, Any], hunt_cfg_any) if isinstance(hunt_cfg_any, dict) else {}

        mana_name_raw_any = hunt_cfg.get('mana_name')
        mana_name_raw: str = cast(str, mana_name_raw_any) if isinstance(mana_name_raw_any, str) else 'mana potion'
        mana_name = _normalize_refill_item_name(mana_name_raw)

        take_mana = _to_int(hunt_cfg.get('take_mana'), default=0)
        mana_leave = _to_int(hunt_cfg.get('mana_leave'), default=0)
        cap_leave = _to_int(hunt_cfg.get('cap_leave'), default=0)

        refill_options: Dict[str, Any] = {
            'manaPotion': {
                'item': mana_name,
                'quantity': max(0, take_mana),
            },
            'healthPotion': {
                'item': 'Health Potion',
                'quantity': 0,
            },
            'healthPotionEnabled': False,
            # Your note: NPC is usually "trade" potions.
            'houseNpcEnabled': False,
        }

        refill_checker_base: Dict[str, Any] = {
            'minimumAmountOfHealthPotions': 0,
            'minimumAmountOfManaPotions': max(0, mana_leave),
            'minimumAmountOfCap': max(0, cap_leave),
            'healthEnabled': False,
            'waypointLabelToRedirect': '',
        }

        # Persist legacy-derived options so scripts can be upgraded even if the
        # user loads the setup before/after loading the pilotscript.
        try:
            if isinstance(self.context, dict):
                self.context.setdefault('ng_legacy', {})
                if isinstance(self.context.get('ng_legacy'), dict):
                    self.context['ng_legacy']['refill_options'] = refill_options
                    self.context['ng_legacy']['refill_checker_base'] = refill_checker_base
        except Exception:
            pass
        try:
            if isinstance(self.enabledProfile, dict) and isinstance(self.enabledProfile.get('config'), dict):
                self.enabledProfile['config'].setdefault('ng_legacy', {})
                if isinstance(self.enabledProfile['config'].get('ng_legacy'), dict):
                    self.enabledProfile['config']['ng_legacy']['refill_options'] = refill_options
                    self.enabledProfile['config']['ng_legacy']['refill_checker_base'] = refill_checker_base
        except Exception:
            pass

        items_any = setup.get('items')
        items: Dict[str, Any] = cast(Dict[str, Any], items_any) if isinstance(items_any, dict) else {}
        spells_any = setup.get('spells')
        spells: Dict[str, Any] = cast(Dict[str, Any], spells_any) if isinstance(spells_any, dict) else {}
        legacy_healing_any = setup.get('healing')
        legacy_healing: List[Any] = cast(List[Any], legacy_healing_any) if isinstance(legacy_healing_any, list) else []

        # Ensure structure exists.
        if 'healing' not in self.context or not isinstance(self.context.get('healing'), dict):
            self.context['healing'] = {}
        healing_cfg = self.context['healing']
        healing_cfg.setdefault('potions', {})
        healing_cfg.setdefault('spells', {})
        healing_cfg.setdefault('eatFood', {})

        potions_cfg = healing_cfg.get('potions')
        spells_cfg = healing_cfg.get('spells')
        eat_cfg = healing_cfg.get('eatFood')
        if not isinstance(potions_cfg, dict):
            potions_cfg = {}
            healing_cfg['potions'] = potions_cfg
        if not isinstance(spells_cfg, dict):
            spells_cfg = {}
            healing_cfg['spells'] = spells_cfg
        if not isinstance(eat_cfg, dict):
            eat_cfg = {}
            healing_cfg['eatFood'] = eat_cfg

        potions_cfg.setdefault('firstManaPotion', {})
        spells_cfg.setdefault('lightHealing', {})
        mana_cfg = potions_cfg.get('firstManaPotion')
        light_cfg = spells_cfg.get('lightHealing')
        if not isinstance(mana_cfg, dict):
            mana_cfg = {}
            potions_cfg['firstManaPotion'] = mana_cfg
        if not isinstance(light_cfg, dict):
            light_cfg = {}
            spells_cfg['lightHealing'] = light_cfg

        # Mana potion hotkey from legacy items.
        item_cfg = items.get(mana_name_raw)
        if isinstance(item_cfg, dict):
            hk = item_cfg.get('hotkey')
            if isinstance(hk, str) and hk.strip():
                mana_cfg['enabled'] = True
                mana_cfg['hotkey'] = hk.strip()

        # Thresholds from legacy healing.
        for rule in legacy_healing:
            if not isinstance(rule, dict):
                continue
            rtype = rule.get('type')
            if rtype == 'mp':
                below = _to_int(rule.get('below_percent'), default=-1)
                if below is not None:
                    mana_cfg['enabled'] = True
                    if below >= 0:
                        mana_cfg['manaPercentageLessThanOrEqual'] = max(0, min(100, below))

            if rtype == 'hp':
                spell_name = rule.get('use_spell')
                if isinstance(spell_name, str) and spell_name.strip():
                    hk = spells.get(spell_name)
                    below = _to_int(rule.get('below_percent'), default=-1)
                    min_mana = _to_int(rule.get('min_mana_percent'), default=0)
                    light_cfg['enabled'] = True
                    light_cfg['spell'] = spell_name.strip()
                    if isinstance(hk, str) and hk.strip():
                        light_cfg['hotkey'] = hk.strip()
                    if below >= 0:
                        light_cfg['hpPercentageLessThanOrEqual'] = max(0, min(100, below))
                    light_cfg['manaPercentageGreaterThanOrEqual'] = max(0, min(100, min_mana))

        # eat_food persistent action
        persistent_actions_any = setup.get('persistent_actions')
        persistent_actions: List[Any] = (
            cast(List[Any], persistent_actions_any) if isinstance(persistent_actions_any, list) else []
        )
        for act in persistent_actions:
            if not isinstance(act, dict) or act.get('action') != 'eat_food':
                continue
            args_any = act.get('args')
            args: Dict[str, Any] = cast(Dict[str, Any], args_any) if isinstance(args_any, dict) else {}
            hk = args.get('hotkey')
            if isinstance(hk, str) and hk.strip():
                eat_cfg['enabled'] = True
                eat_cfg['hotkey'] = hk.strip()
                eat_cfg.setdefault('eatWhenFoodIslessOrEqual', 0)
                break

        # Upgrade current loaded cavebot script if present.
        changed = False
        items_list = None
        try:
            items_list = self.context.get('ng_cave', {}).get('waypoints', {}).get('items')
        except Exception:
            items_list = None

        if isinstance(items_list, list):
            # pyright doesn't know pilotscript element typing here.
            try:
                changed = bool(self._upgradeLegacyWaypointsInPlace(cast(List[Dict[str, Any]], items_list)))
            except Exception:
                changed = False

        # Persist changes.
        try:
            self.enabledProfile['config']['healing'] = self.context.get('healing', {})
            if changed and isinstance(items_list, list):
                self.enabledProfile['config'].setdefault('ng_cave', {})
                self.enabledProfile['config']['ng_cave'].setdefault('waypoints', {})
                self.enabledProfile['config']['ng_cave']['waypoints']['items'] = items_list
            self.db.update(self.enabledProfile)
        except Exception:
            pass

    def _ensureManualAutoAttackConfig(self) -> None:
        if 'manual_auto_attack' not in self.context or not isinstance(self.context.get('manual_auto_attack'), dict):
            self.context['manual_auto_attack'] = {}
        self.context['manual_auto_attack'].setdefault('enabled', False)
        self.context['manual_auto_attack'].setdefault('method', 'hotkey')
        self.context['manual_auto_attack'].setdefault('hotkey', 'pageup')
        self.context['manual_auto_attack'].setdefault('interval_s', 0.70)
        self.context['manual_auto_attack'].setdefault('only_when_not_attacking', False)
        self.context['manual_auto_attack'].setdefault('key_repeat', 1)
        self.context['manual_auto_attack'].setdefault('pre_delay_s', 0.02)
        self.context['manual_auto_attack'].setdefault('click_modifier', 'none')
        self.context['manual_auto_attack'].setdefault('click_button', 'left')
        self.context['manual_auto_attack'].setdefault('focus_before', False)
        self.context['manual_auto_attack'].setdefault('focus_after_s', 0.05)

        # Also ensure persisted profile config has defaults, so partial saves don't
        # drop keys (load merges defaults, but this keeps file.json tidy).
        try:
            if getattr(self, 'enabledProfile', None) is not None and isinstance(self.enabledProfile.get('config'), dict):
                self.enabledProfile['config'].setdefault('manual_auto_attack', {})
                prof = self.enabledProfile['config'].get('manual_auto_attack')
                if not isinstance(prof, dict):
                    self.enabledProfile['config']['manual_auto_attack'] = {}
                    prof = self.enabledProfile['config']['manual_auto_attack']
                prof.setdefault('enabled', False)
                prof.setdefault('method', 'hotkey')
                prof.setdefault('hotkey', 'pageup')
                prof.setdefault('interval_s', 0.70)
                prof.setdefault('only_when_not_attacking', False)
                prof.setdefault('key_repeat', 1)
                prof.setdefault('pre_delay_s', 0.02)
                prof.setdefault('click_modifier', 'none')
                prof.setdefault('click_button', 'left')
                prof.setdefault('focus_before', False)
                prof.setdefault('focus_after_s', 0.05)
        except Exception:
            pass

    def _ensureNgRuntimeConfig(self) -> None:
        if 'ng_runtime' not in self.context or not isinstance(self.context.get('ng_runtime'), dict):
            self.context['ng_runtime'] = {}
        self.context['ng_runtime'].setdefault('attack_from_battlelist', False)
        self.context['ng_runtime'].setdefault('targeting_diag', False)
        self.context['ng_runtime'].setdefault('window_diag', False)
        self.context['ng_runtime'].setdefault('dump_task_on_timeout', False)
        self.context['ng_runtime'].setdefault('status_log_interval_s', 2.0)
        self.context['ng_runtime'].setdefault('loot_modifier', 'shift')
        self.context['ng_runtime'].setdefault('attack_only', False)
        self.context['ng_runtime'].setdefault('allow_attack_without_coord', False)
        self.context['ng_runtime'].setdefault('warn_on_window_miss', False)
        self.context['ng_runtime'].setdefault('action_window_title', '')
        self.context['ng_runtime'].setdefault('capture_window_title', '')
        self.context['ng_runtime'].setdefault('start_paused', True)
        self.context['ng_runtime'].setdefault('depot_open_button', 'left')
        # Attack input defaults (used by clickInClosestCreature)
        self.context['ng_runtime'].setdefault('attack_hotkey', 'space')
        self.context['ng_runtime'].setdefault('attack_click_button', 'left')
        self.context['ng_runtime'].setdefault('attack_safe_click_modifier', 'alt')
        self.context['ng_runtime'].setdefault('battlelist_attack_click_modifier', 'none')
        self.context['ng_runtime'].setdefault('battlelist_attack_click_button', 'left')
        self.context['ng_runtime'].setdefault('battlelist_click_at_cursor', False)
        self.context['ng_runtime'].setdefault('block_right_click_attack', False)
        self.context['ng_runtime'].setdefault('attack_click_pre_delay_s', 0.06)
        self.context['ng_runtime'].setdefault('input_diag', False)
        self.context['ng_runtime'].setdefault('safe_log', False)
        self.context['ng_runtime'].setdefault('console_log', True)
        self.context['ng_runtime'].setdefault('log_level', 'info')
        self.context['ng_runtime'].setdefault('output_idx', 1)
        self.context['ng_runtime'].setdefault('auto_output_idx', True)
        self.context['ng_runtime'].setdefault('mss_fallback_on_none', False)
        self.context['ng_runtime'].setdefault('mss_fallback', False)
        self.context['ng_runtime'].setdefault('black_dark_pixel_threshold', 8)
        self.context['ng_runtime'].setdefault('black_dark_fraction_threshold', 0.98)
        self.context['ng_runtime'].setdefault('black_std_threshold', 1.0)
        self.context['ng_runtime'].setdefault('black_mean_threshold', 2.0)
        self.context['ng_runtime'].setdefault('black_mean_force_threshold', 2.0)
        self.context['ng_runtime'].setdefault('dxcam_retry_on_hard_black', True)
        self.context['ng_runtime'].setdefault('black_frame_threshold', 8)
        self.context['ng_runtime'].setdefault('same_frame_threshold', 30)
        self.context['ng_runtime'].setdefault('dxcam_recover_on_stale', True)
        self.context['ng_runtime'].setdefault('dxcam_recover_on_black', True)
        self.context['ng_runtime'].setdefault('log_dxcam_recovery', True)
        self.context['ng_runtime'].setdefault('diag_black_dump_threshold', 12)
        self.context['ng_runtime'].setdefault('dump_black_capture', False)
        self.context['ng_runtime'].setdefault('dump_black_capture_min_interval_s', 60.0)
        self.context['ng_runtime'].setdefault('arduino_port', 'COM33')
        self.context['ng_runtime'].setdefault('disable_arduino', False)
        self.context['ng_runtime'].setdefault('disable_arduino_clicks', False)
        self.context['ng_runtime'].setdefault('radar_use_previous_on_miss', True)
        self.context['ng_runtime'].setdefault('radar_use_previous_max_ticks', 3)
        self.context['ng_runtime'].setdefault('dump_radar_on_fail', False)
        self.context['ng_runtime'].setdefault('dump_radar_min_interval_s', 60.0)
        self.context['ng_runtime'].setdefault('reset_locator_cache_threshold', 10)
        self.context['ng_runtime'].setdefault('diag_radar_missing_threshold', 30)
        self.context['ng_runtime'].setdefault('diag_arrows_missing_threshold', 30)
        self.context['ng_runtime'].setdefault('dump_radar_persistent', False)
        self.context['ng_runtime'].setdefault('dump_radar_persistent_min_interval_s', 120.0)
        self.context['ng_runtime'].setdefault('warn_on_battlelist_empty', True)
        self.context['ng_runtime'].setdefault('dump_battlelist_on_empty', False)
        self.context['ng_runtime'].setdefault('dump_battlelist_min_interval_s', 120.0)

        if not isinstance(self.context['ng_runtime'].get('task_timeouts'), dict):
            self.context['ng_runtime']['task_timeouts'] = {}
        task_timeouts = self.context['ng_runtime']['task_timeouts']
        try:
            task_timeouts.setdefault('buyItem', 25.0)
            task_timeouts.setdefault('dragItems', 25.0)
            task_timeouts.setdefault('dragItemsToFloor', 25.0)
            task_timeouts.setdefault('dropBackpackIntoStash', 20.0)
            task_timeouts.setdefault('goToFreeDepot', 120.0)
            task_timeouts.setdefault('openBackpack', 12.0)
            task_timeouts.setdefault('openDepot', 10.0)
            task_timeouts.setdefault('openLocker', 12.0)
            task_timeouts.setdefault('scrollToItem', 20.0)
        except Exception:
            pass
        self.context['ng_runtime'].setdefault('radar_tools_confidence', 0.80)
        self.context['ng_runtime'].setdefault('radar_tools_multiscale', True)
        self.context['ng_runtime'].setdefault('radar_tools_min_scale', 0.80)
        self.context['ng_runtime'].setdefault('radar_tools_max_scale', 1.20)
        self.context['ng_runtime'].setdefault('radar_tools_scale_steps', 9)
        self.context['ng_runtime'].setdefault('battlelist_icon_confidence', 0.85)
        self.context['ng_runtime'].setdefault('battlelist_icon_min_scale', 0.70)
        self.context['ng_runtime'].setdefault('battlelist_icon_max_scale', 1.30)
        self.context['ng_runtime'].setdefault('battlelist_icon_scale_steps', 13)
        self.context['ng_runtime'].setdefault('battlelist_bottombar_confidence', 0.85)
        self.context['ng_runtime'].setdefault('battlelist_bottombar_min_scale', 0.70)
        self.context['ng_runtime'].setdefault('battlelist_bottombar_max_scale', 1.30)
        self.context['ng_runtime'].setdefault('battlelist_bottombar_scale_steps', 13)
        self.context['ng_runtime'].setdefault('battlelist_click_x_offset', 60)

        try:
            if getattr(self, 'enabledProfile', None) is not None and isinstance(self.enabledProfile.get('config'), dict):
                self.enabledProfile['config'].setdefault('ng_runtime', {})
                prof = self.enabledProfile['config'].get('ng_runtime')
                if not isinstance(prof, dict):
                    self.enabledProfile['config']['ng_runtime'] = {}
                    prof = self.enabledProfile['config']['ng_runtime']
                prof.setdefault('attack_from_battlelist', False)
                prof.setdefault('targeting_diag', False)
                prof.setdefault('window_diag', False)
                prof.setdefault('dump_task_on_timeout', False)
                prof.setdefault('status_log_interval_s', 2.0)
                prof.setdefault('loot_modifier', 'shift')
                prof.setdefault('attack_only', False)
                prof.setdefault('allow_attack_without_coord', False)
                prof.setdefault('warn_on_window_miss', False)
                prof.setdefault('action_window_title', '')
                prof.setdefault('capture_window_title', '')
                prof.setdefault('start_paused', True)
                prof.setdefault('depot_open_button', 'left')
                # Attack input defaults (used by clickInClosestCreature)
                prof.setdefault('attack_hotkey', 'space')
                prof.setdefault('attack_click_button', 'left')
                prof.setdefault('attack_safe_click_modifier', 'alt')
                prof.setdefault('battlelist_attack_click_modifier', 'none')
                prof.setdefault('battlelist_attack_click_button', 'left')
                prof.setdefault('battlelist_click_at_cursor', False)
                prof.setdefault('block_right_click_attack', False)
                prof.setdefault('attack_click_pre_delay_s', 0.06)
                prof.setdefault('input_diag', False)
                prof.setdefault('safe_log', False)
                prof.setdefault('console_log', True)
                prof.setdefault('log_level', 'info')
                prof.setdefault('output_idx', 1)
                prof.setdefault('auto_output_idx', True)
                prof.setdefault('arduino_port', 'COM33')
                prof.setdefault('disable_arduino', False)
                prof.setdefault('disable_arduino_clicks', False)

                if not isinstance(prof.get('task_timeouts'), dict):
                    prof['task_timeouts'] = {}
                prof_task_timeouts = prof['task_timeouts']
                try:
                    prof_task_timeouts.setdefault('buyItem', 25.0)
                    prof_task_timeouts.setdefault('dragItems', 25.0)
                    prof_task_timeouts.setdefault('dragItemsToFloor', 25.0)
                    prof_task_timeouts.setdefault('dropBackpackIntoStash', 20.0)
                    prof_task_timeouts.setdefault('goToFreeDepot', 120.0)
                    prof_task_timeouts.setdefault('openBackpack', 12.0)
                    prof_task_timeouts.setdefault('openDepot', 10.0)
                    prof_task_timeouts.setdefault('openLocker', 12.0)
                    prof_task_timeouts.setdefault('scrollToItem', 20.0)
                except Exception:
                    pass
        except Exception:
            pass

    def setRuntimeStartPaused(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['start_paused'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['start_paused'] = v
        self.db.update(self.enabledProfile)

    def setWindowTitle(self, window_title: str, persist: bool = True) -> bool:
        self.context['window_title'] = window_title
        windows = gw.getWindowsWithTitle(window_title)
        self.context['window'] = windows[0] if windows else None
        if persist:
            self.enabledProfile['config']['window_title'] = window_title
            self.db.update(self.enabledProfile)
        return self.context['window'] is not None

    def getEnabledProfile(self) -> Dict[str, Any]:
        return self.db.search(Query().enabled == True)[0]

    def updateLootBackpack(self, backpack: str) -> None:
        self.context['ng_backpacks']['loot'] = backpack
        self.enabledProfile['config']['ng_backpacks']['loot'] = backpack
        self.db.update(self.enabledProfile)

    def addWaypoint(self, waypoint: Dict[str, Any]) -> None:
        self.context['ng_cave']['waypoints']['items'].append(waypoint)
        self.enabledProfile['config']['ng_cave']['waypoints']['items'].append(
            waypoint)
        self.db.update(self.enabledProfile)

    def addCombo(self, combo: Dict[str, Any]) -> None:
        self.context['ng_comboSpells']['items'].append(combo)
        self.enabledProfile['config']['ng_comboSpells']['items'].append(
            combo)
        self.db.update(self.enabledProfile)

    def addIgnorableCreature(self, creature: str) -> None:
        self.context['ignorable_creatures'].append(creature)
        self.enabledProfile['config']['ignorable_creatures'].append(creature)
        self.db.update(self.enabledProfile)

    def addSpellByIndex(self, index: int, spell: Dict[str, Any]) -> None:
        self.context['ng_comboSpells']['items'][index]['spells'].append(spell)
        # self.enabledProfile['config']['ng_comboSpells']['items'][index]['spells'].append(
        #     spell)
        self.db.update(self.enabledProfile)

    def getAllWaypointLabels(self) -> List[str]:
        waypointsLabels = [waypointItem['label'] for waypointItem in self.context['ng_cave']
                        ['waypoints']['items'] if waypointItem['label'] != '']
        return waypointsLabels

    def hasWaypointWithLabel(self, label: str, ignoreLabel: Optional[str] = None) -> bool:
        for waypoint in self.context['ng_cave']['waypoints']['items']:
            if waypoint['label'] == label and ignoreLabel is not None:
                return True
        return False

    def updateWaypointByIndex(self, waypointIndex: int, label: Optional[str] = None, options: Optional[Dict[str, Any]] = None) -> None:
        if options is None:
            options = {}
        if label is not None:
            self.context['ng_cave']['waypoints']['items'][waypointIndex]['label'] = label
            self.enabledProfile['config']['ng_cave']['waypoints']['items'][waypointIndex]['label'] = label
        self.context['ng_cave']['waypoints']['items'][waypointIndex]['options'] = options
        self.enabledProfile['config']['ng_cave']['waypoints']['items'][waypointIndex]['options'] = options
        self.db.update(self.enabledProfile)

    def updateIgnorableCreatureByIndex(self, creatureIndex: int, name: Optional[str] = None) -> None:
        if name is not None:
            self.context['ignorable_creatures'][creatureIndex] = name
            self.enabledProfile['config']['ignorable_creatures'][creatureIndex] = name
            self.db.update(self.enabledProfile)

    def removeWaypointByIndex(self, index: int) -> None:
        self.context['ng_cave']['waypoints']['items'].pop(index)
        self.enabledProfile['config']['ng_cave']['waypoints']['items'].pop(
            index)
        self.db.update(self.enabledProfile)

    def removeComboByIndex(self, index: int) -> None:
        self.context['ng_comboSpells']['items'].pop(index)
        self.enabledProfile['config']['ng_comboSpells']['items'].pop(
            index)
        self.db.update(self.enabledProfile)

    def removeIgnorableCreatureByIndex(self, index: int) -> None:
        self.context['ignorable_creatures'].pop(index)
        self.enabledProfile['config']['ignorable_creatures'].pop(index)
        self.db.update(self.enabledProfile)

    def play(self) -> None:
        if self.context['window'] is None:
            messagebox.showerror(
                'Erro', 'Tibia window is not set!')
            return
        self.context['window'].activate()
        time.sleep(1)
        # screenshot = getScreenshot()
        # chatTabs = getTabs(screenshot)
        # if 'loot' not in chatTabs:
        #     messagebox.showerror(
        #         'Erro', 'Loot tab must be open!')
        #     return
        self.context['ng_pause'] = False

    def pause(self) -> None:
        self.context['ng_pause'] = True
        self.context['ng_tasksOrchestrator'].setRootTask(self.context, None)
        self.context['ng_cave']['waypoints']['currentIndex'] = None
        self.context['loot']['corpsesToLoot'] = []
        reset_old_list = cast(Callable[[], None], resetOldList)
        reset_old_list()

    def toggleHealingPotionsByKey(self, healthPotionType: str, enabled: bool) -> None:
        self.context['healing']['potions'][healthPotionType]['enabled'] = enabled
        self.enabledProfile['config']['healing']['potions'][healthPotionType]['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def toggleFoodByKey(self, enabled: bool) -> None:
        self.context['healing']['eatFood']['enabled'] = enabled
        self.enabledProfile['config']['healing']['eatFood']['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def toggleHealingHighPriorityByKey(self, key: str, enabled: bool) -> None:
        self.context['healing']['highPriority'][key]['enabled'] = enabled
        self.enabledProfile['config']['healing']['highPriority'][key]['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def setShovelHotkey(self, hotkey: str) -> None:
        self.context['general_hotkeys']['shovel_hotkey'] = hotkey
        self.enabledProfile['config']['general_hotkeys']['shovel_hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setRopeHotkey(self, hotkey: str) -> None:
        self.context['general_hotkeys']['rope_hotkey'] = hotkey
        self.enabledProfile['config']['general_hotkeys']['rope_hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setManualAutoAttackEnabled(self, enabled: bool) -> None:
        self._ensureManualAutoAttackConfig()
        self.context['manual_auto_attack']['enabled'] = enabled
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def setManualAutoAttackHotkey(self, hotkey: str) -> None:
        self._ensureManualAutoAttackConfig()
        self.context['manual_auto_attack']['hotkey'] = hotkey
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setManualAutoAttackInterval(self, interval_s: float) -> None:
        self._ensureManualAutoAttackConfig()
        # Keep sane bounds.
        try:
            interval_s = float(interval_s)
        except Exception:
            interval_s = 0.70
        if interval_s < 0.10:
            interval_s = 0.10
        if interval_s > 5.0:
            interval_s = 5.0
        self.context['manual_auto_attack']['interval_s'] = interval_s
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['interval_s'] = interval_s
        self.db.update(self.enabledProfile)

    def setManualAutoAttackMethod(self, method: str) -> None:
        self._ensureManualAutoAttackConfig()
        method_norm = (method or '').strip().lower()
        if method_norm not in {'hotkey', 'click'}:
            method_norm = 'hotkey'
        self.context['manual_auto_attack']['method'] = method_norm
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['method'] = method_norm
        self.db.update(self.enabledProfile)

    def setManualAutoAttackOnlyWhenNotAttacking(self, enabled: bool) -> None:
        self._ensureManualAutoAttackConfig()
        self.context['manual_auto_attack']['only_when_not_attacking'] = bool(enabled)
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['only_when_not_attacking'] = bool(enabled)
        self.db.update(self.enabledProfile)

    def setManualAutoAttackKeyRepeat(self, repeats: int) -> None:
        self._ensureManualAutoAttackConfig()
        try:
            repeats_i = int(repeats)
        except Exception:
            repeats_i = 1
        if repeats_i < 1:
            repeats_i = 1
        if repeats_i > 3:
            repeats_i = 3
        self.context['manual_auto_attack']['key_repeat'] = repeats_i
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['key_repeat'] = repeats_i
        self.db.update(self.enabledProfile)

    def setManualAutoAttackPreDelay(self, delay_s: float) -> None:
        self._ensureManualAutoAttackConfig()
        try:
            v = float(delay_s)
        except Exception:
            v = 0.02
        if v < 0:
            v = 0.0
        if v > 1.0:
            v = 1.0
        self.context['manual_auto_attack']['pre_delay_s'] = v
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['pre_delay_s'] = v
        self.db.update(self.enabledProfile)

    def setManualAutoAttackClickModifier(self, modifier: str) -> None:
        self._ensureManualAutoAttackConfig()
        mod = (modifier or '').strip().lower()
        if mod in {'control', 'ctl'}:
            mod = 'ctrl'
        if mod not in {'none', 'ctrl', 'alt', 'shift'}:
            mod = 'none'
        self.context['manual_auto_attack']['click_modifier'] = mod
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['click_modifier'] = mod
        self.db.update(self.enabledProfile)

    def setManualAutoAttackClickButton(self, button: str) -> None:
        self._ensureManualAutoAttackConfig()
        btn = (button or '').strip().lower()
        if btn not in {'left', 'right'}:
            btn = 'left'
        self.context['manual_auto_attack']['click_button'] = btn
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['click_button'] = btn
        self.db.update(self.enabledProfile)

    def setManualAutoAttackFocusBefore(self, enabled: bool) -> None:
        self._ensureManualAutoAttackConfig()
        self.context['manual_auto_attack']['focus_before'] = bool(enabled)
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['focus_before'] = bool(enabled)
        self.db.update(self.enabledProfile)

    def setManualAutoAttackFocusAfter(self, delay_s: float) -> None:
        self._ensureManualAutoAttackConfig()
        try:
            v = float(delay_s)
        except Exception:
            v = 0.05
        if v < 0:
            v = 0.0
        if v > 1.0:
            v = 1.0
        self.context['manual_auto_attack']['focus_after_s'] = v
        self.enabledProfile['config'].setdefault('manual_auto_attack', {})
        self.enabledProfile['config']['manual_auto_attack']['focus_after_s'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeAttackFromBattlelist(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['attack_from_battlelist'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['attack_from_battlelist'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeTargetingDiag(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['targeting_diag'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['targeting_diag'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeWindowDiag(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['window_diag'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['window_diag'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeDumpTaskOnTimeout(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['dump_task_on_timeout'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['dump_task_on_timeout'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeStatusLogInterval(self, interval_s: float) -> None:
        self._ensureNgRuntimeConfig()
        try:
            v = float(interval_s)
        except Exception:
            v = 2.0
        if v < 0.25:
            v = 0.25
        if v > 30.0:
            v = 30.0
        self.context['ng_runtime']['status_log_interval_s'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['status_log_interval_s'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeLootModifier(self, modifier: str) -> None:
        self._ensureNgRuntimeConfig()
        mod = (modifier or '').strip().lower()
        if mod in {'control', 'ctl'}:
            mod = 'ctrl'
        if mod not in {'none', 'shift', 'ctrl', 'alt'}:
            mod = 'shift'
        self.context['ng_runtime']['loot_modifier'] = mod
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['loot_modifier'] = mod
        self.db.update(self.enabledProfile)

    def setRuntimeAttackOnly(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['attack_only'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['attack_only'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeAllowAttackWithoutCoord(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['allow_attack_without_coord'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['allow_attack_without_coord'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeWarnOnWindowMiss(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['warn_on_window_miss'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['warn_on_window_miss'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeActionWindowTitle(self, title: str) -> None:
        self._ensureNgRuntimeConfig()
        v = (title or '').strip()
        self.context['ng_runtime']['action_window_title'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['action_window_title'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeCaptureWindowTitle(self, title: str) -> None:
        self._ensureNgRuntimeConfig()
        v = (title or '').strip()
        self.context['ng_runtime']['capture_window_title'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['capture_window_title'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeDepotOpenButton(self, button: str) -> None:
        self._ensureNgRuntimeConfig()
        btn = (button or '').strip().lower()
        if btn not in {'left', 'right'}:
            btn = 'right'
        self.context['ng_runtime']['depot_open_button'] = btn
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['depot_open_button'] = btn
        self.db.update(self.enabledProfile)

    def setRuntimeAttackHotkey(self, hotkey: str) -> None:
        self._ensureNgRuntimeConfig()
        v = (hotkey or '').strip().lower()
        if v == '':
            v = 'space'
        self.context['ng_runtime']['attack_hotkey'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['attack_hotkey'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeAttackClickButton(self, button: str) -> None:
        self._ensureNgRuntimeConfig()
        btn = (button or '').strip().lower()
        if btn not in {'left', 'right'}:
            btn = 'left'
        self.context['ng_runtime']['attack_click_button'] = btn
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['attack_click_button'] = btn
        self.db.update(self.enabledProfile)

    def setRuntimeAttackSafeClickModifier(self, modifier: str) -> None:
        self._ensureNgRuntimeConfig()
        mod = (modifier or '').strip().lower()
        if mod in {'control', 'ctl'}:
            mod = 'ctrl'
        if mod not in {'none', 'shift', 'ctrl', 'alt'}:
            mod = 'alt'
        self.context['ng_runtime']['attack_safe_click_modifier'] = mod
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['attack_safe_click_modifier'] = mod
        self.db.update(self.enabledProfile)

    def setRuntimeBattlelistAttackClickModifier(self, modifier: str) -> None:
        self._ensureNgRuntimeConfig()
        mod = (modifier or '').strip().lower()
        if mod in {'control', 'ctl'}:
            mod = 'ctrl'
        if mod not in {'none', 'shift', 'ctrl', 'alt'}:
            mod = 'none'
        self.context['ng_runtime']['battlelist_attack_click_modifier'] = mod
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['battlelist_attack_click_modifier'] = mod
        self.db.update(self.enabledProfile)

    def setRuntimeBattlelistAttackClickButton(self, button: str) -> None:
        self._ensureNgRuntimeConfig()
        btn = (button or '').strip().lower()
        if btn not in {'left', 'right'}:
            btn = 'left'
        self.context['ng_runtime']['battlelist_attack_click_button'] = btn
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['battlelist_attack_click_button'] = btn
        self.db.update(self.enabledProfile)

    def setRuntimeBattlelistClickAtCursor(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['battlelist_click_at_cursor'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['battlelist_click_at_cursor'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeBlockRightClickAttack(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['block_right_click_attack'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['block_right_click_attack'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeAttackClickPreDelay(self, delay_s: float) -> None:
        self._ensureNgRuntimeConfig()
        try:
            v = float(delay_s)
        except Exception:
            v = 0.06
        if v < 0:
            v = 0.0
        if v > 0.5:
            v = 0.5
        self.context['ng_runtime']['attack_click_pre_delay_s'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['attack_click_pre_delay_s'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeInputDiag(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['input_diag'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['input_diag'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_mouse(input_diag=v)
        except Exception:
            pass

    def setRuntimeSafeLog(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['safe_log'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['safe_log'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_safe_log(enabled=v)
        except Exception:
            pass

    def setRuntimeConsoleLog(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['console_log'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['console_log'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_console_log(enabled=v)
        except Exception:
            pass

    def setRuntimeLogLevel(self, level: str) -> None:
        self._ensureNgRuntimeConfig()
        v = (level or '').strip().lower()
        if v not in {'debug', 'info', 'warn', 'error'}:
            v = 'info'
        self.context['ng_runtime']['log_level'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['log_level'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_console_log(level=v)
        except Exception:
            pass

    def setRuntimeOutputIdx(self, output_idx: int) -> None:
        self._ensureNgRuntimeConfig()
        try:
            v = int(output_idx)
        except Exception:
            v = 1
        if v < 1:
            v = 1
        self.context['ng_runtime']['output_idx'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['output_idx'] = v
        self.db.update(self.enabledProfile)
        try:
            setScreenshotOutputIdx(v)
        except Exception:
            pass

    def setRuntimeAutoOutputIdx(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['auto_output_idx'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['auto_output_idx'] = v
        self.db.update(self.enabledProfile)

    def setRuntimeArduinoPort(self, port: str) -> None:
        self._ensureNgRuntimeConfig()
        v = (port or '').strip() or 'COM33'
        self.context['ng_runtime']['arduino_port'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['arduino_port'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_arduino(port=v)
        except Exception:
            pass

    def setRuntimeDisableArduino(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['disable_arduino'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['disable_arduino'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_arduino(disable_arduino=v)
        except Exception:
            pass

    def setRuntimeDisableArduinoClicks(self, enabled: bool) -> None:
        self._ensureNgRuntimeConfig()
        v = bool(enabled)
        self.context['ng_runtime']['disable_arduino_clicks'] = v
        self.enabledProfile['config'].setdefault('ng_runtime', {})
        self.enabledProfile['config']['ng_runtime']['disable_arduino_clicks'] = v
        self.db.update(self.enabledProfile)
        try:
            configure_arduino(disable_clicks=v)
        except Exception:
            pass
        try:
            configure_mouse(disable_arduino_clicks=v)
        except Exception:
            pass

    def setRuntimeTaskTimeout(self, task_key: str, seconds: float) -> None:
        self._ensureNgRuntimeConfig()
        key = (task_key or '').strip()
        if key == '':
            return
        try:
            v = float(seconds)
        except Exception:
            return
        if v < 0.25:
            v = 0.25
        if v > 600.0:
            v = 600.0

        if not isinstance(self.context['ng_runtime'].get('task_timeouts'), dict):
            self.context['ng_runtime']['task_timeouts'] = {}
        self.context['ng_runtime']['task_timeouts'][key] = v

        self.enabledProfile['config'].setdefault('ng_runtime', {})
        if not isinstance(self.enabledProfile['config']['ng_runtime'].get('task_timeouts'), dict):
            self.enabledProfile['config']['ng_runtime']['task_timeouts'] = {}
        self.enabledProfile['config']['ng_runtime']['task_timeouts'][key] = v
        self.db.update(self.enabledProfile)

    def setHotkeyHealingHighPriorityByKey(self, key: str, hotkey: str) -> None:
        self.context['healing']['highPriority'][key]['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['highPriority'][key]['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setHealthFoodHpPercentageLessThanOrEqual(self, hpPercentageLessThanOrEqual: int) -> None:
        self.context['healing']['highPriority']['healthFood']['hpPercentageLessThanOrEqual'] = hpPercentageLessThanOrEqual
        self.enabledProfile['config']['healing']['highPriority']['healthFood'][
            'hpPercentageLessThanOrEqual'] = hpPercentageLessThanOrEqual
        self.db.update(self.enabledProfile)

    def setManaFoodHpPercentageLessThanOrEqual(self, manaPercentageLessThanOrEqual: int) -> None:
        self.context['healing']['highPriority']['manaFood']['manaPercentageLessThanOrEqual'] = manaPercentageLessThanOrEqual
        self.enabledProfile['config']['healing']['highPriority']['manaFood'][
            'manaPercentageLessThanOrEqual'] = manaPercentageLessThanOrEqual
        self.db.update(self.enabledProfile)

    def toggleSpellByKey(self, healthPotionType: str, enabled: bool) -> None:
        self.context['healing']['spells'][healthPotionType]['enabled'] = enabled
        self.enabledProfile['config']['healing']['spells'][healthPotionType]['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def setFoodHotkey(self, hotkey: str) -> None:
        self.context['healing']['eatFood']['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['eatFood']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setHealthPotionHotkeyByKey(self, healthPotionType: str, hotkey: str) -> None:
        self.context['healing']['potions'][healthPotionType]['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['potions'][healthPotionType]['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setHealthPotionSlotByKey(self, healthPotionType: str, slot: int) -> None:
        self.context['healing']['potions'][healthPotionType]['slot'] = slot
        self.enabledProfile['config']['healing']['potions'][healthPotionType]['slot'] = slot
        self.db.update(self.enabledProfile)

    def setSpellHotkeyByKey(self, healthPotionType: str, hotkey: str) -> None:
        self.context['healing']['spells'][healthPotionType]['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['spells'][healthPotionType]['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setHealthPotionHpPercentageLessThanOrEqual(self, healthPotionType: str, hpPercentage: int) -> None:
        self.context['healing']['potions'][healthPotionType]['hpPercentageLessThanOrEqual'] = hpPercentage
        self.enabledProfile['config']['healing']['potions'][healthPotionType]['hpPercentageLessThanOrEqual'] = hpPercentage
        self.db.update(self.enabledProfile)

    def setSwapRingHpPercentageLessThanOrEqual(self, hpPercentageLessThanOrEqual: int) -> None:
        self.context['healing']['highPriority']['swapRing']['tankRing']['hpPercentageLessThanOrEqual'] = hpPercentageLessThanOrEqual
        self.enabledProfile['config']['healing']['highPriority']['swapRing']['tankRing'][
            'hpPercentageLessThanOrEqual'] = hpPercentageLessThanOrEqual
        self.db.update(self.enabledProfile)

    def setSwapTankRingHotkey(self, hotkey: str) -> None:
        self.context['healing']['highPriority']['swapRing']['tankRing']['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['highPriority']['swapRing']['tankRing']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setSwapTankRingSlotByKey(self, slot: int) -> None:
        self.context['healing']['highPriority']['swapRing']['tankRing']['slot'] = slot
        self.enabledProfile['config']['healing']['highPriority']['swapRing']['tankRing']['slot'] = slot
        self.db.update(self.enabledProfile)

    def setSwapMainRingSlotByKey(self, slot: int) -> None:
        self.context['healing']['highPriority']['swapRing']['mainRing']['slot'] = slot
        self.enabledProfile['config']['healing']['highPriority']['swapRing']['mainRing']['slot'] = slot
        self.db.update(self.enabledProfile)

    def setSwapMainRingHotkey(self, hotkey: str) -> None:
        self.context['healing']['highPriority']['swapRing']['mainRing']['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['highPriority']['swapRing']['mainRing']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setSwapRingHpPercentageGreaterThan(self, hpPercentageGreaterThan: int) -> None:
        self.context['healing']['highPriority']['swapRing']['mainRing']['hpPercentageGreaterThan'] = hpPercentageGreaterThan
        self.enabledProfile['config']['healing']['highPriority']['swapRing']['mainRing'][
            'hpPercentageGreaterThan'] = hpPercentageGreaterThan
        self.db.update(self.enabledProfile)

    def setSwapAmuletHpPercentageLessThanOrEqual(self, hpPercentageLessThanOrEqual: int) -> None:
        self.context['healing']['highPriority']['swapAmulet']['tankAmulet']['hpPercentageLessThanOrEqual'] = hpPercentageLessThanOrEqual
        self.enabledProfile['config']['healing']['highPriority']['swapAmulet']['tankAmulet'][
            'hpPercentageLessThanOrEqual'] = hpPercentageLessThanOrEqual
        self.db.update(self.enabledProfile)

    def setSwapAmuletHpPercentageGreaterThan(self, hpPercentageGreaterThan: int) -> None:
        self.context['healing']['highPriority']['swapAmulet']['mainAmulet']['hpPercentageGreaterThan'] = hpPercentageGreaterThan
        self.enabledProfile['config']['healing']['highPriority']['swapAmulet']['mainAmulet'][
            'hpPercentageGreaterThan'] = hpPercentageGreaterThan
        self.db.update(self.enabledProfile)

    def setSwapTankAmuletHotkey(self, hotkey: str) -> None:
        self.context['healing']['highPriority']['swapAmulet']['tankAmulet']['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['highPriority']['swapAmulet']['tankAmulet']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setSwapMainAmuletHotkey(self, hotkey: str) -> None:
        self.context['healing']['highPriority']['swapAmulet']['mainAmulet']['hotkey'] = hotkey
        self.enabledProfile['config']['healing']['highPriority']['swapAmulet']['mainAmulet']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setSwapTankAmuletSlotByKey(self, slot: int) -> None:
        self.context['healing']['highPriority']['swapAmulet']['tankAmulet']['slot'] = slot
        self.enabledProfile['config']['healing']['highPriority']['swapAmulet']['tankAmulet']['slot'] = slot
        self.db.update(self.enabledProfile)

    def setSwapMainAmuletSlotByKey(self, slot: int) -> None:
        self.context['healing']['highPriority']['swapAmulet']['mainAmulet']['slot'] = slot
        self.enabledProfile['config']['healing']['highPriority']['swapAmulet']['mainAmulet']['slot'] = slot
        self.db.update(self.enabledProfile)

    def setSpellHpPercentageLessThanOrEqual(self, spellType: str, hpPercentage: int) -> None:
        self.context['healing']['spells'][spellType]['hpPercentageLessThanOrEqual'] = hpPercentage
        self.enabledProfile['config']['healing']['spells'][spellType]['hpPercentageLessThanOrEqual'] = hpPercentage
        self.db.update(self.enabledProfile)

    def setSpellManaPercentageGreaterThanOrEqual(self, spellType: str, hpPercentage: int) -> None:
        self.context['healing']['spells'][spellType]['manaPercentageGreaterThanOrEqual'] = hpPercentage
        self.enabledProfile['config']['healing']['spells'][spellType]['manaPercentageGreaterThanOrEqual'] = hpPercentage
        self.db.update(self.enabledProfile)

    def setSpellName(self, spellType: str, spell: Optional[str]) -> None:
        self.context['healing']['spells'][spellType]['spell'] = spell
        self.enabledProfile['config']['healing']['spells'][spellType]['spell'] = spell
        self.db.update(self.enabledProfile)

    def setHealthPotionManaPercentageGreaterThanOrEqual(self, healthPotionType: str, hpPercentage: int) -> None:
        self.context['healing']['potions'][healthPotionType]['manaPercentageGreaterThanOrEqual'] = hpPercentage
        self.enabledProfile['config']['healing']['potions'][healthPotionType]['manaPercentageGreaterThanOrEqual'] = hpPercentage
        self.db.update(self.enabledProfile)

    def setHealthPotionManaPercentageLessThanOrEqual(self, healthPotionType: str, hpPercentage: int) -> None:
        self.context['healing']['potions'][healthPotionType]['manaPercentageLessThanOrEqual'] = hpPercentage
        self.enabledProfile['config']['healing']['potions'][healthPotionType]['manaPercentageLessThanOrEqual'] = hpPercentage
        self.db.update(self.enabledProfile)

    def toggleCavebot(self, enabled: bool) -> None:
        self.context['ng_cave']['enabled'] = enabled
        self.enabledProfile['config']['ng_cave']['enabled'] = enabled
        self.db.update(self.enabledProfile)
        log('info', f"Cavebot enabled={enabled}")
        if enabled and self.context.get('ng_pause'):
            self.play()

    def toggleRunToCreatures(self, enabled: bool) -> None:
        self.context['ng_cave']['runToCreatures'] = enabled
        self.enabledProfile['config']['ng_cave']['runToCreatures'] = enabled
        self.db.update(self.enabledProfile)

    def toggleComboSpells(self, enabled: bool) -> None:
        self.context['ng_comboSpells']['enabled'] = enabled
        self.enabledProfile['config']['ng_comboSpells']['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def toggleSingleCombo(self, enabled: bool, index: int) -> None:
        self.context['ng_comboSpells']['items'][index]['enabled'] = enabled
        self.enabledProfile['config']['ng_comboSpells']['items'][index]['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def removeSpellByIndex(self, index: int, indexTable: int) -> None:
        self.context['ng_comboSpells']['items'][index]['spells'].pop(indexTable)
        # self.enabledProfile['config']['ng_comboSpells']['items'][index]['spells'].pop(
        #     index)
        self.db.update(self.enabledProfile)

    def changeComboName(self, name: str, index: int) -> None:
        self.context['ng_comboSpells']['items'][index]['name'] = name
        self.enabledProfile['config']['ng_comboSpells']['items'][index]['name'] = name
        self.db.update(self.enabledProfile)

    def setCompare(self, compare: str, index: int) -> None:
        self.context['ng_comboSpells']['items'][index]['creatures']['compare'] = compare
        self.enabledProfile['config']['ng_comboSpells']['items'][index]['creatures']['compare'] = compare
        self.db.update(self.enabledProfile)

    def changeCompareValue(self, value: str, index: int) -> None:
        if not value:
            return
        self.context['ng_comboSpells']['items'][index]['creatures']['value'] = int(value)
        self.enabledProfile['config']['ng_comboSpells']['items'][index]['creatures']['value'] = int(value)
        self.db.update(self.enabledProfile)

    def setComboSpellName(self, name: str, index: int, indexSecond: int) -> None:
        self.context['ng_comboSpells']['items'][index]['spells'][indexSecond]['name'] = name
        self.enabledProfile['config']['ng_comboSpells']['items'][index]['spells'][indexSecond]['name'] = name
        self.db.update(self.enabledProfile)

    def setComboSpellHotkey(self, key: str, index: int, indexSecond: int) -> None:
        self.context['ng_comboSpells']['items'][index]['spells'][indexSecond]['hotkey'] = key
        self.enabledProfile['config']['ng_comboSpells']['items'][index]['spells'][indexSecond]['hotkey'] = key
        self.db.update(self.enabledProfile)

    def toggleAutoHur(self, enabled: bool) -> None:
        self.context['auto_hur']['enabled'] = enabled
        self.enabledProfile['config']['auto_hur']['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def toggleAutoHurPz(self, enabled: bool) -> None:
        self.context['auto_hur']['pz'] = enabled
        self.enabledProfile['config']['auto_hur']['pz'] = enabled
        self.db.update(self.enabledProfile)

    def setAutoHurHotkey(self, hotkey: str) -> None:
        self.context['auto_hur']['hotkey'] = hotkey
        self.enabledProfile['config']['auto_hur']['hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def setAutoHurSpell(self, spell: str) -> None:
        self.context['auto_hur']['spell'] = spell
        self.enabledProfile['config']['auto_hur']['spell'] = spell
        self.db.update(self.enabledProfile)

    def toggleAlert(self, enabled: bool) -> None:
        self.context['alert']['enabled'] = enabled
        self.enabledProfile['config']['alert']['enabled'] = enabled
        self.db.update(self.enabledProfile)

    def toggleAlertCave(self, enabled: bool) -> None:
        self.context['alert']['cave'] = enabled
        self.enabledProfile['config']['alert']['cave'] = enabled
        self.db.update(self.enabledProfile)

    def toggleAlertSayPlayer(self, enabled: bool) -> None:
        self.context['alert']['sayPlayer'] = enabled
        self.enabledProfile['config']['alert']['sayPlayer'] = enabled
        self.db.update(self.enabledProfile)

    def toggleClearStatsPoison(self, enabled: bool) -> None:
        self.context['clear_stats']['poison'] = enabled
        self.enabledProfile['config']['clear_stats']['poison'] = enabled
        self.db.update(self.enabledProfile)

    def setClearStatsPoisonHotkey(self, hotkey: str) -> None:
        self.context['clear_stats']['poison_hotkey'] = hotkey
        self.enabledProfile['config']['clear_stats']['poison_hotkey'] = hotkey
        self.db.update(self.enabledProfile)

    def toggleManaPotionsByKey(self, manaPotionType: str, enabled: bool) -> None:
        self.context['healing']['potions'][manaPotionType]['enabled'] = enabled

    def setManaPotionManaPercentageLessThanOrEqual(self, manaPotionType: str, manaPercentage: int) -> None:
        self.context['healing']['potions'][manaPotionType]['manaPercentageLessThanOrEqual'] = manaPercentage

    def toggleHealingSpellsByKey(self, contextKey: str, enabled: bool) -> None:
        self.context['healing']['spells'][contextKey]['enabled'] = enabled

    def setHealingSpellsHpPercentage(self, contextKey: str, hpPercentage: int) -> None:
        self.context['healing']['spells'][contextKey]['hpPercentageLessThanOrEqual'] = hpPercentage

    def setHealingSpellsHotkey(self, contextKey: str, hotkey: str) -> None:
        self.context['healing']['spells'][contextKey]['hotkey'] = hotkey
