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
        window_title = self.enabledProfile['config'].get('window_title')
        if window_title:
            self.setWindowTitle(window_title, persist=False)

    def updateMainBackpack(self, backpack: str) -> None:
        self.context['ng_backpacks']['main'] = backpack
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
        self.context['ng_cave']['waypoints']['items'] = script.copy()
        self.enabledProfile['config']['ng_cave']['waypoints']['items'] = script.copy()
        self.db.update(self.enabledProfile)

    def loadCfg(self, cfg: Dict[str, Any]) -> None:
        load_cfgs = cast(Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]], loadNgCfgs)
        self.context = load_cfgs(cfg, self.context)
        self.enabledProfile['config']['ng_backpacks'] = self.context['ng_backpacks']
        self.enabledProfile['config']['general_hotkeys'] = self.context['general_hotkeys']
        self.enabledProfile['config']['auto_hur'] = self.context['auto_hur']
        self.enabledProfile['config']['alert'] = self.context['alert']
        self.enabledProfile['config']['clear_stats'] = self.context['clear_stats']
        self.enabledProfile['config']['manual_auto_attack'] = self.context.get('manual_auto_attack', {})
        self.enabledProfile['config']['ng_runtime'] = self.context.get('ng_runtime', {})
        self.enabledProfile['config']['ng_comboSpells']['enabled'] = self.context['ng_comboSpells']['enabled']
        self.enabledProfile['config']['ng_comboSpells']['items'] = []
        for comboSpellsItem in self.context['ng_comboSpells']['items']:
            comboSpellsItem['currentSpellIndex'] = 0
            self.enabledProfile['config']['ng_comboSpells']['items'].append(comboSpellsItem)
        self.enabledProfile['config']['healing'] = self.context['healing']
        self.db.update(self.enabledProfile)

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
