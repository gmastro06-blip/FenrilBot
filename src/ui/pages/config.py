import pygetwindow as gw
import re
import win32gui
import customtkinter
import tkinter as tk
from typing import Any, List
from src.ui.utils import genRanStr
from tkinter import filedialog, messagebox
import json

class ConfigPage(customtkinter.CTkToplevel):
    def __init__(self, context: Any) -> None:
        super().__init__()
        self.context = context

        self.title(genRanStr())
        self.resizable(False, False)

        self.windowsFrame = customtkinter.CTkFrame(self)
        self.windowsFrame.grid(column=0, row=0, padx=10,
                            pady=10, sticky='nsew')

        self.windowsFrame.rowconfigure(0, weight=1)
        self.windowsFrame.columnconfigure(0, weight=1)

        self.tibiaWindowLabel = customtkinter.CTkLabel(self.windowsFrame, text="Game Window:")
        self.tibiaWindowLabel.grid(row=0, column=0, sticky='w', padx=10, pady=(10, 0))

        self.windowsCombobox = customtkinter.CTkComboBox(
            self.windowsFrame, values=self.getGameWindows(), state='readonly',
            command=self.onChangeWindow)
        self.windowsCombobox.grid(row=1, column=0, sticky='ew', padx=10, pady=10)
        saved_title = self.context.context.get('window_title')
        if saved_title:
            current_values = self.windowsCombobox.cget('values')
            if saved_title in current_values:
                self.windowsCombobox.set(saved_title)

        self.button = customtkinter.CTkButton(
            self.windowsFrame, text='Atualizar', command=self.refreshWindows,
            corner_radius=32, fg_color="transparent", border_color="#C20034",
            border_width=2, hover_color="#C20034")
        self.button.grid(row=1, column=1, padx=10, pady=10)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.shovelRopeFrame = customtkinter.CTkFrame(self)
        self.shovelRopeFrame.grid(column=1, row=0, padx=10,
                            pady=10, sticky='nsew')

        self.shovelHotkeyLabel = customtkinter.CTkLabel(
            self.shovelRopeFrame, text='Shovel Hotkey:')
        self.shovelHotkeyLabel.grid(column=0, row=0, padx=10,
                            pady=10, sticky='nsew')

        self.shovelHotkeyEntryVar = tk.StringVar()
        self.shovelHotkeyEntryVar.set(self.context.context['general_hotkeys']['shovel_hotkey'])
        self.shovelHotkeyEntry = customtkinter.CTkEntry(self.shovelRopeFrame, textvariable=self.shovelHotkeyEntryVar)
        self.shovelHotkeyEntry.bind('<Key>', self.onChangeShovelHotkey)
        self.shovelHotkeyEntry.grid(column=1, row=0, padx=10,
                            pady=10, sticky='nsew')
        
        self.ropeHotkeyLabel = customtkinter.CTkLabel(
            self.shovelRopeFrame, text='Rope Hotkey:')
        self.ropeHotkeyLabel.grid(column=0, row=1, padx=10,
                            pady=10, sticky='nsew')

        self.ropeHotkeyEntryVar = tk.StringVar()
        self.ropeHotkeyEntryVar.set(self.context.context['general_hotkeys']['rope_hotkey'])
        self.ropeHotkeyEntry = customtkinter.CTkEntry(self.shovelRopeFrame, textvariable=self.ropeHotkeyEntryVar)
        self.ropeHotkeyEntry.bind('<Key>', self.onChangeRopeHotkey)
        self.ropeHotkeyEntry.grid(column=1, row=1, padx=10,
                            pady=10, sticky='nsew')
        
        self.shovelRopeFrame.columnconfigure(0, weight=1)
        self.shovelRopeFrame.columnconfigure(1, weight=1)

        self.autoHurFrame = customtkinter.CTkFrame(self)
        self.autoHurFrame.grid(column=0, row=1, padx=10,
                            pady=10, sticky='nsew')
        
        self.checkVar = tk.BooleanVar()
        self.checkVar.set(
            self.context.context['auto_hur']['enabled'])
        self.checkbutton = customtkinter.CTkCheckBox(
            self.autoHurFrame, text='Enabled', variable=self.checkVar, command=self.onToggleAutoHur,
            hover_color="#870125", fg_color='#C20034')
        self.checkbutton.grid(column=0, row=0, sticky='nsew', padx=10, pady=10)

        self.checkPzVar = tk.BooleanVar()
        self.checkPzVar.set(
            self.context.context['auto_hur']['pz'])
        self.checkpzbutton = customtkinter.CTkCheckBox(
            self.autoHurFrame, text='Usar em PZ', variable=self.checkPzVar, command=self.onToggleAutoHurPz,
            hover_color="#870125", fg_color='#C20034')
        self.checkpzbutton.grid(column=1, row=0, sticky='nsew', padx=10, pady=10)

        self.autoHurSpellLabel = customtkinter.CTkLabel(
            self.autoHurFrame, text='Spell:')
        self.autoHurSpellLabel.grid(column=0, row=1, padx=10,
                            pady=10, sticky='nsew')

        self.hurSpellCombobox = customtkinter.CTkComboBox(
            self.autoHurFrame, values=['utani hur', 'utani gran hur', 'utani tempo hur', 'utamo tempo san'], state='readonly',
            command=self.setHurSpell)
        if self.context.enabledProfile is not None and self.context.enabledProfile['config']['auto_hur']['spell'] is not None:
            self.hurSpellCombobox.set(
                self.context.enabledProfile['config']['auto_hur']['spell'])
        self.hurSpellCombobox.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')
        
        self.autoHurLabel = customtkinter.CTkLabel(
            self.autoHurFrame, text='AutoHur Hotkey:')
        self.autoHurLabel.grid(column=0, row=2, padx=10,
                            pady=10, sticky='nsew')

        self.autoHurHotkeyEntryVar = tk.StringVar()
        self.autoHurHotkeyEntryVar.set(self.context.context['auto_hur']['hotkey'])
        self.autoHurHotkeyEntry = customtkinter.CTkEntry(self.autoHurFrame, textvariable=self.autoHurHotkeyEntryVar)
        self.autoHurHotkeyEntry.bind('<Key>', self.onChangeAutoHurHotkey)
        self.autoHurHotkeyEntry.grid(column=1, row=2, padx=10,
                            pady=10, sticky='nsew')
        
        self.autoHurFrame.columnconfigure(0, weight=1)
        self.autoHurFrame.columnconfigure(1, weight=1)

        self.alertFrame = customtkinter.CTkFrame(self)
        self.alertFrame.grid(column=1, row=1, padx=10,
                            pady=10, sticky='nsew')
        
        self.alertCheckVar = tk.BooleanVar()
        self.alertCheckVar.set(
            self.context.context['alert']['enabled'])
        self.alertCheckButton = customtkinter.CTkCheckBox(
            self.alertFrame, text='Alert Enabled', variable=self.alertCheckVar, command=self.onToggleAlert,
            hover_color="#870125", fg_color='#C20034')
        self.alertCheckButton.grid(column=0, row=0, sticky='nsew', padx=10, pady=10)

        self.alertCaveCheckVar = tk.BooleanVar()
        self.alertCaveCheckVar.set(
            self.context.context['alert']['cave'])
        self.alertCaveButton = customtkinter.CTkCheckBox(
            self.alertFrame, text='Apenas cave ativo', variable=self.alertCaveCheckVar, command=self.onToggleAlertCave,
            hover_color="#870125", fg_color='#C20034')
        self.alertCaveButton.grid(column=1, row=0, sticky='nsew', padx=10, pady=10)

        self.alertSayPlayerCheckVar = tk.BooleanVar()
        self.alertSayPlayerCheckVar.set(
            self.context.context['alert']['sayPlayer'])
        self.alertCheckButton = customtkinter.CTkCheckBox(
            self.alertFrame, text='Enviar ? para Player', variable=self.alertSayPlayerCheckVar, command=self.onToggleAlertSayPlayer,
            hover_color="#870125", fg_color='#C20034')
        self.alertCheckButton.grid(column=0, row=1, sticky='nsew', padx=10, pady=10)
        
        self.alertFrame.columnconfigure(0, weight=1)
        self.alertFrame.columnconfigure(1, weight=1)

        self.clearStatsFrame = customtkinter.CTkFrame(self)
        self.clearStatsFrame.grid(column=0, row=2, padx=10,
                            pady=10, sticky='nsew')
        
        self.checkPoisonVar = tk.BooleanVar()
        self.checkPoisonVar.set(
            self.context.context['clear_stats']['poison'])
        self.checkPoisonButton = customtkinter.CTkCheckBox(
            self.clearStatsFrame, text='Limpar poison', variable=self.checkPoisonVar, command=self.onTogglePoison,
            hover_color="#870125", fg_color='#C20034')
        self.checkPoisonButton.grid(column=0, row=0, sticky='nsew', padx=10, pady=10)
        
        self.poisonLabel = customtkinter.CTkLabel(
            self.clearStatsFrame, text='Poison Hotkey:')
        self.poisonLabel.grid(column=0, row=1, padx=10,
                            pady=10, sticky='nsew')

        self.poisonHotkeyEntryVar = tk.StringVar()
        self.poisonHotkeyEntryVar.set(self.context.context['clear_stats']['poison_hotkey'])
        self.poisonHotkeyEntry = customtkinter.CTkEntry(self.clearStatsFrame, textvariable=self.poisonHotkeyEntryVar)
        self.poisonHotkeyEntry.bind('<Key>', self.onChangePoisonHotkey)
        self.poisonHotkeyEntry.grid(column=1, row=1, padx=10,
                            pady=10, sticky='nsew')
        
        self.clearStatsFrame.columnconfigure(0, weight=1)
        self.clearStatsFrame.columnconfigure(1, weight=1)

        self.saveConfigFrame = customtkinter.CTkFrame(self)
        self.saveConfigFrame.grid(column=1, row=2, padx=10,
                            pady=10, sticky='nsew')

        saveConfigButton = customtkinter.CTkButton(self.saveConfigFrame, text="Save Cfg", corner_radius=32,
                                        fg_color="transparent", border_color="#C20034",
                                        border_width=2, hover_color="#C20034", command=self.saveCfg)
        saveConfigButton.grid(row=0, column=0, padx=20, pady=20, sticky='nsew')

        loadConfigButton = customtkinter.CTkButton(self.saveConfigFrame, text="Load Cfg", corner_radius=32,
                                        fg_color="transparent", border_color="#C20034",
                                        border_width=2, hover_color="#C20034", command=self.loadCfg)
        loadConfigButton.grid(row=0, column=1, padx=20, pady=20, sticky='nsew')
        
        self.saveConfigFrame.columnconfigure(0, weight=1)
        self.saveConfigFrame.columnconfigure(1, weight=1)

        # Manual auto-attack (next target) configuration
        self.manualAttackFrame = customtkinter.CTkFrame(self)
        self.manualAttackFrame.grid(column=0, row=3, columnspan=2, padx=10, pady=10, sticky='nsew')
        self.manualAttackFrame.columnconfigure(0, weight=1)
        self.manualAttackFrame.columnconfigure(1, weight=1)
        self.manualAttackFrame.columnconfigure(2, weight=1)

        self.manualAttackEnabledVar = tk.BooleanVar()
        try:
            self.manualAttackEnabledVar.set(bool(self.context.context.get('manual_auto_attack', {}).get('enabled', False)))
        except Exception:
            self.manualAttackEnabledVar.set(False)

        self.manualAttackEnabledCheck = customtkinter.CTkCheckBox(
            self.manualAttackFrame,
            text='Manual Auto-Attack (Hotkey)',
            variable=self.manualAttackEnabledVar,
            command=self.onToggleManualAutoAttack,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.manualAttackEnabledCheck.grid(column=0, row=0, padx=10, pady=10, sticky='w')

        self.manualAttackHotkeyLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Next Target Hotkey:')
        self.manualAttackHotkeyLabel.grid(column=0, row=1, padx=10, pady=10, sticky='w')

        self.manualAttackHotkeyVar = tk.StringVar()
        try:
            self.manualAttackHotkeyVar.set(str(self.context.context.get('manual_auto_attack', {}).get('hotkey', 'pageup')))
        except Exception:
            self.manualAttackHotkeyVar.set('pageup')
        self.manualAttackHotkeyEntry = customtkinter.CTkEntry(self.manualAttackFrame, textvariable=self.manualAttackHotkeyVar)
        self.manualAttackHotkeyEntry.bind('<Key>', self.onChangeManualAutoAttackHotkey)
        self.manualAttackHotkeyEntry.grid(column=1, row=1, padx=10, pady=10, sticky='ew')

        self.manualAttackIntervalLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Interval (s):')
        self.manualAttackIntervalLabel.grid(column=0, row=2, padx=10, pady=(10, 0), sticky='w')

        self.manualAttackIntervalValueLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='')
        self.manualAttackIntervalValueLabel.grid(column=2, row=2, padx=10, pady=(10, 0), sticky='e')

        self.manualAttackIntervalVar = tk.DoubleVar()
        try:
            self.manualAttackIntervalVar.set(float(self.context.context.get('manual_auto_attack', {}).get('interval_s', 0.70)))
        except Exception:
            self.manualAttackIntervalVar.set(0.70)

        self.manualAttackIntervalSlider = customtkinter.CTkSlider(
            self.manualAttackFrame,
            from_=0.10,
            to=2.00,
            number_of_steps=190,
            variable=self.manualAttackIntervalVar,
            command=self.onChangeManualAutoAttackInterval,
            fg_color="#333333",
            progress_color="#C20034",
            button_color="#C20034",
            button_hover_color="#870125",
        )
        self.manualAttackIntervalSlider.grid(column=1, row=2, padx=10, pady=(10, 0), sticky='ew')
        self._updateManualAutoAttackIntervalLabel()

        # Runtime settings (persisted in profile: ng_runtime)
        self.runtimeFrame = customtkinter.CTkFrame(self)
        self.runtimeFrame.grid(column=0, row=4, columnspan=2, padx=10, pady=10, sticky='nsew')
        self.runtimeFrame.columnconfigure(0, weight=1)
        self.runtimeFrame.columnconfigure(1, weight=1)
        self.runtimeFrame.columnconfigure(2, weight=1)

        self.runtimeTitle = customtkinter.CTkLabel(self.runtimeFrame, text='Runtime')
        self.runtimeTitle.grid(column=0, row=0, padx=10, pady=(10, 0), sticky='w')

        ng_runtime = self.context.context.get('ng_runtime', {})

        self.runtimeAttackFromBLVar = tk.BooleanVar()
        self.runtimeTargetingDiagVar = tk.BooleanVar()
        self.runtimeWindowDiagVar = tk.BooleanVar()
        self.runtimeDumpTimeoutVar = tk.BooleanVar()
        self.runtimeStartPausedVar = tk.BooleanVar()
        self.runtimeAttackOnlyVar = tk.BooleanVar()
        self.runtimeAllowAttackWithoutCoordVar = tk.BooleanVar()
        self.runtimeWarnOnWindowMissVar = tk.BooleanVar()

        try:
            self.runtimeAttackFromBLVar.set(bool(ng_runtime.get('attack_from_battlelist', False)))
        except Exception:
            self.runtimeAttackFromBLVar.set(False)
        try:
            self.runtimeTargetingDiagVar.set(bool(ng_runtime.get('targeting_diag', False)))
        except Exception:
            self.runtimeTargetingDiagVar.set(False)
        try:
            self.runtimeWindowDiagVar.set(bool(ng_runtime.get('window_diag', False)))
        except Exception:
            self.runtimeWindowDiagVar.set(False)
        try:
            self.runtimeDumpTimeoutVar.set(bool(ng_runtime.get('dump_task_on_timeout', False)))
        except Exception:
            self.runtimeDumpTimeoutVar.set(False)

        try:
            self.runtimeStartPausedVar.set(bool(ng_runtime.get('start_paused', True)))
        except Exception:
            self.runtimeStartPausedVar.set(True)
        try:
            self.runtimeAttackOnlyVar.set(bool(ng_runtime.get('attack_only', False)))
        except Exception:
            self.runtimeAttackOnlyVar.set(False)
        try:
            self.runtimeAllowAttackWithoutCoordVar.set(bool(ng_runtime.get('allow_attack_without_coord', False)))
        except Exception:
            self.runtimeAllowAttackWithoutCoordVar.set(False)
        try:
            self.runtimeWarnOnWindowMissVar.set(bool(ng_runtime.get('warn_on_window_miss', False)))
        except Exception:
            self.runtimeWarnOnWindowMissVar.set(False)
        # (dedup) runtime vars are already initialized above

        self.runtimeAttackFromBLCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Attack-from-battlelist fallback',
            variable=self.runtimeAttackFromBLVar,
            command=self.onToggleRuntimeAttackFromBattlelist,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeAttackFromBLCheck.grid(column=0, row=1, padx=10, pady=(10, 0), sticky='w')

        self.runtimeTargetingDiagCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Targeting diagnostics',
            variable=self.runtimeTargetingDiagVar,
            command=self.onToggleRuntimeTargetingDiag,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeTargetingDiagCheck.grid(column=1, row=1, padx=10, pady=(10, 0), sticky='w')

        self.runtimeWindowDiagCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Window diagnostics',
            variable=self.runtimeWindowDiagVar,
            command=self.onToggleRuntimeWindowDiag,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeWindowDiagCheck.grid(column=2, row=1, padx=10, pady=(10, 0), sticky='w')

        self.runtimeDumpTimeoutCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Dump screenshot on task timeout',
            variable=self.runtimeDumpTimeoutVar,
            command=self.onToggleRuntimeDumpTimeout,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeDumpTimeoutCheck.grid(column=0, row=2, padx=10, pady=(10, 0), sticky='w')

        self.runtimeStartPausedCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Start paused',
            variable=self.runtimeStartPausedVar,
            command=self.onToggleRuntimeStartPaused,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeStartPausedCheck.grid(column=1, row=2, padx=10, pady=(10, 0), sticky='w')

        self.runtimeAttackOnlyCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Attack-only (no movement)',
            variable=self.runtimeAttackOnlyVar,
            command=self.onToggleRuntimeAttackOnly,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeAttackOnlyCheck.grid(column=2, row=2, padx=10, pady=(10, 0), sticky='w')

        # (dedup) keep a single Attack-only checkbox and a single allow-attack-without-coord checkbox

        self.runtimeStatusIntervalLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Status log interval (s):')
        self.runtimeStatusIntervalLabel.grid(column=0, row=3, padx=10, pady=(10, 10), sticky='w')
        self.runtimeStatusIntervalVar = tk.StringVar()
        try:
            self.runtimeStatusIntervalVar.set(str(float(ng_runtime.get('status_log_interval_s', 2.0))))
        except Exception:
            self.runtimeStatusIntervalVar.set('2.0')
        self.runtimeStatusIntervalEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeStatusIntervalVar)
        self.runtimeStatusIntervalEntry.bind('<KeyRelease>', self.onChangeRuntimeStatusInterval)
        self.runtimeStatusIntervalEntry.bind('<FocusOut>', self.onChangeRuntimeStatusInterval)
        self.runtimeStatusIntervalEntry.grid(column=1, row=3, padx=10, pady=(10, 10), sticky='ew')

        self.runtimeLootModifierLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Loot modifier:')
        self.runtimeLootModifierLabel.grid(column=2, row=3, padx=10, pady=(10, 0), sticky='w')
        self.runtimeLootModifierCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['shift', 'ctrl', 'alt', 'none'],
            state='readonly',
            command=self.onChangeRuntimeLootModifier,
        )
        self.runtimeLootModifierCombo.grid(column=2, row=4, padx=10, pady=(10, 10), sticky='ew')
        try:
            self.runtimeLootModifierCombo.set(str(ng_runtime.get('loot_modifier', 'shift')))
        except Exception:
            self.runtimeLootModifierCombo.set('shift')

        self.runtimeWarnOnWindowMissCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Warn on window miss',
            variable=self.runtimeWarnOnWindowMissVar,
            command=self.onToggleRuntimeWarnOnWindowMiss,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeWarnOnWindowMissCheck.grid(column=0, row=4, padx=10, pady=(10, 10), sticky='w')

        self.runtimeAllowAttackWithoutCoordCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Allow attack without coord',
            variable=self.runtimeAllowAttackWithoutCoordVar,
            command=self.onToggleRuntimeAllowAttackWithoutCoord,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeAllowAttackWithoutCoordCheck.grid(column=1, row=4, padx=10, pady=(10, 10), sticky='w')

        self.runtimeActionTitleLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Action window title:')
        self.runtimeActionTitleLabel.grid(column=0, row=5, padx=10, pady=(10, 0), sticky='w')
        self.runtimeActionTitleVar = tk.StringVar()
        try:
            self.runtimeActionTitleVar.set(str(ng_runtime.get('action_window_title', '') or ''))
        except Exception:
            self.runtimeActionTitleVar.set('')
        self.runtimeActionTitleEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeActionTitleVar)
        self.runtimeActionTitleEntry.bind('<KeyRelease>', self.onChangeRuntimeActionWindowTitle)
        self.runtimeActionTitleEntry.bind('<FocusOut>', self.onChangeRuntimeActionWindowTitle)
        self.runtimeActionTitleEntry.grid(column=1, row=5, columnspan=2, padx=10, pady=(10, 0), sticky='ew')

        self.runtimeCaptureTitleLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Capture window title:')
        self.runtimeCaptureTitleLabel.grid(column=0, row=6, padx=10, pady=(10, 10), sticky='w')
        self.runtimeCaptureTitleVar = tk.StringVar()
        try:
            self.runtimeCaptureTitleVar.set(str(ng_runtime.get('capture_window_title', '') or ''))
        except Exception:
            self.runtimeCaptureTitleVar.set('')
        self.runtimeCaptureTitleEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeCaptureTitleVar)
        self.runtimeCaptureTitleEntry.bind('<KeyRelease>', self.onChangeRuntimeCaptureWindowTitle)
        self.runtimeCaptureTitleEntry.bind('<FocusOut>', self.onChangeRuntimeCaptureWindowTitle)
        self.runtimeCaptureTitleEntry.grid(column=1, row=6, columnspan=2, padx=10, pady=(10, 10), sticky='ew')

        self.runtimeDepotOpenButtonLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Depot open button:')
        self.runtimeDepotOpenButtonLabel.grid(column=0, row=7, padx=10, pady=(10, 10), sticky='w')
        self.runtimeDepotOpenButtonCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['right', 'left'],
            state='readonly',
            command=self.onChangeRuntimeDepotOpenButton,
        )
        self.runtimeDepotOpenButtonCombo.grid(column=1, row=7, padx=10, pady=(10, 10), sticky='w')
        try:
            self.runtimeDepotOpenButtonCombo.set(str(ng_runtime.get('depot_open_button', 'right')))
        except Exception:
            self.runtimeDepotOpenButtonCombo.set('right')

        # Attack input settings (used by clickInClosestCreature)
        self.runtimeAttackHotkeyLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Attack hotkey:')
        self.runtimeAttackHotkeyLabel.grid(column=0, row=8, padx=10, pady=(10, 0), sticky='w')
        self.runtimeAttackHotkeyVar = tk.StringVar()
        try:
            self.runtimeAttackHotkeyVar.set(str(ng_runtime.get('attack_hotkey', 'space') or 'space'))
        except Exception:
            self.runtimeAttackHotkeyVar.set('space')
        self.runtimeAttackHotkeyEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeAttackHotkeyVar)
        self.runtimeAttackHotkeyEntry.bind('<KeyRelease>', self.onChangeRuntimeAttackHotkey)
        self.runtimeAttackHotkeyEntry.bind('<FocusOut>', self.onChangeRuntimeAttackHotkey)
        self.runtimeAttackHotkeyEntry.grid(column=1, row=8, padx=10, pady=(10, 0), sticky='ew')

        self.runtimeAttackClickButtonLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Attack click button:')
        self.runtimeAttackClickButtonLabel.grid(column=2, row=8, padx=10, pady=(10, 0), sticky='w')
        self.runtimeAttackClickButtonCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['left', 'right'],
            state='readonly',
            command=self.onChangeRuntimeAttackClickButton,
        )
        self.runtimeAttackClickButtonCombo.grid(column=2, row=9, padx=10, pady=(6, 10), sticky='ew')
        try:
            self.runtimeAttackClickButtonCombo.set(str(ng_runtime.get('attack_click_button', 'left')))
        except Exception:
            self.runtimeAttackClickButtonCombo.set('left')

        self.runtimeAttackSafeModifierLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Safe click modifier:')
        self.runtimeAttackSafeModifierLabel.grid(column=0, row=9, padx=10, pady=(6, 0), sticky='w')
        self.runtimeAttackSafeModifierCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['alt', 'ctrl', 'shift', 'none'],
            state='readonly',
            command=self.onChangeRuntimeAttackSafeClickModifier,
        )
        self.runtimeAttackSafeModifierCombo.grid(column=0, row=10, padx=10, pady=(6, 10), sticky='ew')
        try:
            self.runtimeAttackSafeModifierCombo.set(str(ng_runtime.get('attack_safe_click_modifier', 'alt')))
        except Exception:
            self.runtimeAttackSafeModifierCombo.set('alt')

        self.runtimeBlockRightClickAttackVar = tk.BooleanVar()
        try:
            self.runtimeBlockRightClickAttackVar.set(bool(ng_runtime.get('block_right_click_attack', False)))
        except Exception:
            self.runtimeBlockRightClickAttackVar.set(False)
        self.runtimeBlockRightClickAttackCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Block right-click attack',
            variable=self.runtimeBlockRightClickAttackVar,
            command=self.onToggleRuntimeBlockRightClickAttack,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeBlockRightClickAttackCheck.grid(column=1, row=9, padx=10, pady=(6, 10), sticky='w')

        self.runtimeAttackClickPreDelayLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Attack click pre-delay (s):')
        self.runtimeAttackClickPreDelayLabel.grid(column=1, row=10, padx=10, pady=(6, 10), sticky='w')
        self.runtimeAttackClickPreDelayVar = tk.StringVar()
        try:
            self.runtimeAttackClickPreDelayVar.set(str(float(ng_runtime.get('attack_click_pre_delay_s', 0.06))))
        except Exception:
            self.runtimeAttackClickPreDelayVar.set('0.06')
        self.runtimeAttackClickPreDelayEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeAttackClickPreDelayVar)
        self.runtimeAttackClickPreDelayEntry.bind('<KeyRelease>', self.onChangeRuntimeAttackClickPreDelay)
        self.runtimeAttackClickPreDelayEntry.bind('<FocusOut>', self.onChangeRuntimeAttackClickPreDelay)
        self.runtimeAttackClickPreDelayEntry.grid(column=2, row=10, padx=10, pady=(6, 10), sticky='ew')

        self.runtimeBattlelistModifierLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Battlelist click modifier:')
        self.runtimeBattlelistModifierLabel.grid(column=0, row=11, padx=10, pady=(10, 0), sticky='w')
        self.runtimeBattlelistModifierCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['none', 'alt', 'ctrl', 'shift'],
            state='readonly',
            command=self.onChangeRuntimeBattlelistAttackClickModifier,
        )
        self.runtimeBattlelistModifierCombo.grid(column=0, row=12, padx=10, pady=(6, 10), sticky='ew')
        try:
            self.runtimeBattlelistModifierCombo.set(str(ng_runtime.get('battlelist_attack_click_modifier', 'none')))
        except Exception:
            self.runtimeBattlelistModifierCombo.set('none')

        self.runtimeBattlelistButtonLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Battlelist click button:')
        self.runtimeBattlelistButtonLabel.grid(column=1, row=11, padx=10, pady=(10, 0), sticky='w')
        self.runtimeBattlelistButtonCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['left', 'right'],
            state='readonly',
            command=self.onChangeRuntimeBattlelistAttackClickButton,
        )
        self.runtimeBattlelistButtonCombo.grid(column=1, row=12, padx=10, pady=(6, 10), sticky='ew')
        try:
            self.runtimeBattlelistButtonCombo.set(str(ng_runtime.get('battlelist_attack_click_button', 'left')))
        except Exception:
            self.runtimeBattlelistButtonCombo.set('left')

        self.runtimeBattlelistClickAtCursorVar = tk.BooleanVar()
        try:
            self.runtimeBattlelistClickAtCursorVar.set(bool(ng_runtime.get('battlelist_click_at_cursor', False)))
        except Exception:
            self.runtimeBattlelistClickAtCursorVar.set(False)
        self.runtimeBattlelistClickAtCursorCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Battlelist: click at cursor',
            variable=self.runtimeBattlelistClickAtCursorVar,
            command=self.onToggleRuntimeBattlelistClickAtCursor,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeBattlelistClickAtCursorCheck.grid(column=2, row=12, padx=10, pady=(6, 10), sticky='w')

        # Advanced runtime settings
        self.runtimeOutputIdxLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Capture output idx:')
        self.runtimeOutputIdxLabel.grid(column=0, row=13, padx=10, pady=(10, 0), sticky='w')
        self.runtimeOutputIdxVar = tk.StringVar()
        try:
            self.runtimeOutputIdxVar.set(str(int(float(ng_runtime.get('output_idx', 1)))))
        except Exception:
            self.runtimeOutputIdxVar.set('1')
        self.runtimeOutputIdxEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeOutputIdxVar)
        self.runtimeOutputIdxEntry.bind('<KeyRelease>', self.onChangeRuntimeOutputIdx)
        self.runtimeOutputIdxEntry.bind('<FocusOut>', self.onChangeRuntimeOutputIdx)
        self.runtimeOutputIdxEntry.grid(column=1, row=13, padx=10, pady=(10, 0), sticky='w')

        self.runtimeAutoOutputIdxVar = tk.BooleanVar()
        try:
            self.runtimeAutoOutputIdxVar.set(bool(ng_runtime.get('auto_output_idx', True)))
        except Exception:
            self.runtimeAutoOutputIdxVar.set(True)
        self.runtimeAutoOutputIdxCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Auto output by window monitor',
            variable=self.runtimeAutoOutputIdxVar,
            command=self.onToggleRuntimeAutoOutputIdx,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeAutoOutputIdxCheck.grid(column=2, row=13, padx=10, pady=(10, 0), sticky='w')

        self.runtimeConsoleLogVar = tk.BooleanVar()
        try:
            self.runtimeConsoleLogVar.set(bool(ng_runtime.get('console_log', True)))
        except Exception:
            self.runtimeConsoleLogVar.set(True)
        self.runtimeConsoleLogCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Console log enabled',
            variable=self.runtimeConsoleLogVar,
            command=self.onToggleRuntimeConsoleLog,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeConsoleLogCheck.grid(column=0, row=14, padx=10, pady=(10, 0), sticky='w')

        self.runtimeLogLevelLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Log level:')
        self.runtimeLogLevelLabel.grid(column=1, row=14, padx=10, pady=(10, 0), sticky='w')
        self.runtimeLogLevelCombo = customtkinter.CTkComboBox(
            self.runtimeFrame,
            values=['debug', 'info', 'warn', 'error'],
            state='readonly',
            command=self.onChangeRuntimeLogLevel,
        )
        self.runtimeLogLevelCombo.grid(column=2, row=14, padx=10, pady=(10, 0), sticky='w')
        try:
            self.runtimeLogLevelCombo.set(str(ng_runtime.get('log_level', 'info')))
        except Exception:
            self.runtimeLogLevelCombo.set('info')

        self.runtimeSafeLogVar = tk.BooleanVar()
        try:
            self.runtimeSafeLogVar.set(bool(ng_runtime.get('safe_log', False)))
        except Exception:
            self.runtimeSafeLogVar.set(False)
        self.runtimeSafeLogCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Safety telemetry (debug)',
            variable=self.runtimeSafeLogVar,
            command=self.onToggleRuntimeSafeLog,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeSafeLogCheck.grid(column=0, row=15, padx=10, pady=(10, 0), sticky='w')

        self.runtimeInputDiagVar = tk.BooleanVar()
        try:
            self.runtimeInputDiagVar.set(bool(ng_runtime.get('input_diag', False)))
        except Exception:
            self.runtimeInputDiagVar.set(False)
        self.runtimeInputDiagCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Input diagnostics (click backend)',
            variable=self.runtimeInputDiagVar,
            command=self.onToggleRuntimeInputDiag,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeInputDiagCheck.grid(column=1, row=15, padx=10, pady=(10, 0), sticky='w')

        self.runtimeDisableArduinoVar = tk.BooleanVar()
        try:
            self.runtimeDisableArduinoVar.set(bool(ng_runtime.get('disable_arduino', False)))
        except Exception:
            self.runtimeDisableArduinoVar.set(False)
        self.runtimeDisableArduinoCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Disable Arduino backend',
            variable=self.runtimeDisableArduinoVar,
            command=self.onToggleRuntimeDisableArduino,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeDisableArduinoCheck.grid(column=2, row=15, padx=10, pady=(10, 0), sticky='w')

        self.runtimeDisableArduinoClicksVar = tk.BooleanVar()
        try:
            self.runtimeDisableArduinoClicksVar.set(bool(ng_runtime.get('disable_arduino_clicks', False)))
        except Exception:
            self.runtimeDisableArduinoClicksVar.set(False)
        self.runtimeDisableArduinoClicksCheck = customtkinter.CTkCheckBox(
            self.runtimeFrame,
            text='Disable Arduino clicks only',
            variable=self.runtimeDisableArduinoClicksVar,
            command=self.onToggleRuntimeDisableArduinoClicks,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.runtimeDisableArduinoClicksCheck.grid(column=0, row=16, padx=10, pady=(10, 10), sticky='w')

        self.runtimeArduinoPortLabel = customtkinter.CTkLabel(self.runtimeFrame, text='Arduino port:')
        self.runtimeArduinoPortLabel.grid(column=1, row=16, padx=10, pady=(10, 10), sticky='w')
        self.runtimeArduinoPortVar = tk.StringVar()
        try:
            self.runtimeArduinoPortVar.set(str(ng_runtime.get('arduino_port', 'COM33') or 'COM33'))
        except Exception:
            self.runtimeArduinoPortVar.set('COM33')
        self.runtimeArduinoPortEntry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=self.runtimeArduinoPortVar)
        self.runtimeArduinoPortEntry.bind('<KeyRelease>', self.onChangeRuntimeArduinoPort)
        self.runtimeArduinoPortEntry.bind('<FocusOut>', self.onChangeRuntimeArduinoPort)
        self.runtimeArduinoPortEntry.grid(column=2, row=16, padx=10, pady=(10, 10), sticky='ew')

        # Task timeouts (advanced)
        task_timeouts = {}
        try:
            tt = ng_runtime.get('task_timeouts', {})
            if isinstance(tt, dict):
                task_timeouts = tt
        except Exception:
            task_timeouts = {}

        self.runtimeTaskTimeoutTitle = customtkinter.CTkLabel(self.runtimeFrame, text='Task timeouts (s)')
        self.runtimeTaskTimeoutTitle.grid(column=0, row=17, padx=10, pady=(10, 0), sticky='w')

        self.runtimeTaskTimeoutResetButton = customtkinter.CTkButton(
            self.runtimeFrame,
            text='Reset timeouts',
            command=self.onResetRuntimeTaskTimeouts,
            corner_radius=16,
            fg_color="transparent",
            border_color="#C20034",
            border_width=2,
            hover_color="#C20034",
        )
        self.runtimeTaskTimeoutResetButton.grid(column=2, row=17, padx=10, pady=(10, 0), sticky='e')

        self.runtimeTaskTimeoutVars = {}
        timeout_specs = [
            ('buyItem', 'Buy item', 25.0),
            ('dragItems', 'Drag items', 25.0),
            ('dragItemsToFloor', 'Drag items to floor', 25.0),
            ('dropBackpackIntoStash', 'Drop backpack into stash', 20.0),
            ('goToFreeDepot', 'Go to free depot', 120.0),
            ('openBackpack', 'Open backpack', 12.0),
            ('openDepot', 'Open depot', 10.0),
            ('openLocker', 'Open locker', 12.0),
            ('scrollToItem', 'Scroll to item', 20.0),
        ]
        self.runtimeTaskTimeoutSpecs = timeout_specs

        row = 18
        for key, label, default in timeout_specs:
            lbl = customtkinter.CTkLabel(self.runtimeFrame, text=f'{label}:')
            lbl.grid(column=0, row=row, padx=10, pady=(6, 0), sticky='w')

            var = tk.StringVar()
            try:
                var.set(str(float(task_timeouts.get(key, default))))
            except Exception:
                var.set(str(default))
            self.runtimeTaskTimeoutVars[key] = var

            entry = customtkinter.CTkEntry(self.runtimeFrame, textvariable=var)
            entry.bind('<KeyRelease>', lambda _e, k=key: self.onChangeRuntimeTaskTimeout(k))
            entry.bind('<FocusOut>', lambda _e, k=key: self.onChangeRuntimeTaskTimeout(k))
            entry.grid(column=1, row=row, padx=10, pady=(6, 0), sticky='ew')
            row += 1

        # (dedup) window/warn controls already exist above

        # Advanced manual auto-attack settings
        self.manualAttackMethodLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Method:')
        self.manualAttackMethodLabel.grid(column=0, row=3, padx=10, pady=(10, 0), sticky='w')

        self.manualAttackMethodVar = tk.StringVar()
        try:
            self.manualAttackMethodVar.set(str(self.context.context.get('manual_auto_attack', {}).get('method', 'hotkey')))
        except Exception:
            self.manualAttackMethodVar.set('hotkey')
        self.manualAttackMethodCombo = customtkinter.CTkComboBox(
            self.manualAttackFrame,
            values=['hotkey', 'click'],
            state='readonly',
            command=self.onChangeManualAutoAttackMethod,
        )
        self.manualAttackMethodCombo.grid(column=1, row=3, padx=10, pady=(10, 0), sticky='ew')
        try:
            self.manualAttackMethodCombo.set(self.manualAttackMethodVar.get())
        except Exception:
            self.manualAttackMethodCombo.set('hotkey')

        self.manualAttackOnlyWhenNotAttackingVar = tk.BooleanVar()
        try:
            self.manualAttackOnlyWhenNotAttackingVar.set(bool(self.context.context.get('manual_auto_attack', {}).get('only_when_not_attacking', False)))
        except Exception:
            self.manualAttackOnlyWhenNotAttackingVar.set(False)
        self.manualAttackOnlyWhenNotAttackingCheck = customtkinter.CTkCheckBox(
            self.manualAttackFrame,
            text='Only when NOT attacking',
            variable=self.manualAttackOnlyWhenNotAttackingVar,
            command=self.onToggleManualAutoAttackOnlyWhenNotAttacking,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.manualAttackOnlyWhenNotAttackingCheck.grid(column=0, row=4, padx=10, pady=(10, 0), sticky='w')

        self.manualAttackFocusBeforeVar = tk.BooleanVar()
        try:
            self.manualAttackFocusBeforeVar.set(bool(self.context.context.get('manual_auto_attack', {}).get('focus_before', False)))
        except Exception:
            self.manualAttackFocusBeforeVar.set(False)
        self.manualAttackFocusBeforeCheck = customtkinter.CTkCheckBox(
            self.manualAttackFrame,
            text='Focus Tibia window before input',
            variable=self.manualAttackFocusBeforeVar,
            command=self.onToggleManualAutoAttackFocusBefore,
            hover_color="#870125",
            fg_color='#C20034'
        )
        self.manualAttackFocusBeforeCheck.grid(column=1, row=4, padx=10, pady=(10, 0), sticky='w')

        self.manualAttackKeyRepeatLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Key repeat (1-3):')
        self.manualAttackKeyRepeatLabel.grid(column=0, row=5, padx=10, pady=(10, 0), sticky='w')
        self.manualAttackKeyRepeatVar = tk.StringVar()
        try:
            self.manualAttackKeyRepeatVar.set(str(int(self.context.context.get('manual_auto_attack', {}).get('key_repeat', 1))))
        except Exception:
            self.manualAttackKeyRepeatVar.set('1')
        self.manualAttackKeyRepeatEntry = customtkinter.CTkEntry(self.manualAttackFrame, textvariable=self.manualAttackKeyRepeatVar)
        self.manualAttackKeyRepeatEntry.bind('<KeyRelease>', self.onChangeManualAutoAttackKeyRepeat)
        self.manualAttackKeyRepeatEntry.bind('<FocusOut>', self.onChangeManualAutoAttackKeyRepeat)
        self.manualAttackKeyRepeatEntry.grid(column=1, row=5, padx=10, pady=(10, 0), sticky='ew')

        self.manualAttackPreDelayLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Pre-delay (s):')
        self.manualAttackPreDelayLabel.grid(column=0, row=6, padx=10, pady=(10, 0), sticky='w')
        self.manualAttackPreDelayVar = tk.StringVar()
        try:
            self.manualAttackPreDelayVar.set(str(float(self.context.context.get('manual_auto_attack', {}).get('pre_delay_s', 0.02))))
        except Exception:
            self.manualAttackPreDelayVar.set('0.02')
        self.manualAttackPreDelayEntry = customtkinter.CTkEntry(self.manualAttackFrame, textvariable=self.manualAttackPreDelayVar)
        self.manualAttackPreDelayEntry.bind('<KeyRelease>', self.onChangeManualAutoAttackPreDelay)
        self.manualAttackPreDelayEntry.bind('<FocusOut>', self.onChangeManualAutoAttackPreDelay)
        self.manualAttackPreDelayEntry.grid(column=1, row=6, padx=10, pady=(10, 0), sticky='ew')

        self.manualAttackFocusAfterLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Focus-after delay (s):')
        self.manualAttackFocusAfterLabel.grid(column=0, row=7, padx=10, pady=(10, 10), sticky='w')
        self.manualAttackFocusAfterVar = tk.StringVar()
        try:
            self.manualAttackFocusAfterVar.set(str(float(self.context.context.get('manual_auto_attack', {}).get('focus_after_s', 0.05))))
        except Exception:
            self.manualAttackFocusAfterVar.set('0.05')
        self.manualAttackFocusAfterEntry = customtkinter.CTkEntry(self.manualAttackFrame, textvariable=self.manualAttackFocusAfterVar)
        self.manualAttackFocusAfterEntry.bind('<KeyRelease>', self.onChangeManualAutoAttackFocusAfter)
        self.manualAttackFocusAfterEntry.bind('<FocusOut>', self.onChangeManualAutoAttackFocusAfter)
        self.manualAttackFocusAfterEntry.grid(column=1, row=7, padx=10, pady=(10, 10), sticky='ew')

        self.manualAttackClickModifierLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Click modifier:')
        self.manualAttackClickModifierLabel.grid(column=2, row=3, padx=10, pady=(10, 0), sticky='w')
        self.manualAttackClickModifierCombo = customtkinter.CTkComboBox(
            self.manualAttackFrame,
            values=['none', 'ctrl', 'alt', 'shift'],
            state='readonly',
            command=self.onChangeManualAutoAttackClickModifier,
        )
        self.manualAttackClickModifierCombo.grid(column=2, row=4, padx=10, pady=(10, 0), sticky='ew')
        try:
            self.manualAttackClickModifierCombo.set(str(self.context.context.get('manual_auto_attack', {}).get('click_modifier', 'none')))
        except Exception:
            self.manualAttackClickModifierCombo.set('none')

        self.manualAttackClickButtonLabel = customtkinter.CTkLabel(self.manualAttackFrame, text='Click button:')
        self.manualAttackClickButtonLabel.grid(column=2, row=5, padx=10, pady=(10, 0), sticky='w')
        self.manualAttackClickButtonCombo = customtkinter.CTkComboBox(
            self.manualAttackFrame,
            values=['left', 'right'],
            state='readonly',
            command=self.onChangeManualAutoAttackClickButton,
        )
        self.manualAttackClickButtonCombo.grid(column=2, row=6, padx=10, pady=(10, 0), sticky='ew')
        try:
            self.manualAttackClickButtonCombo.set(str(self.context.context.get('manual_auto_attack', {}).get('click_button', 'left')))
        except Exception:
            self.manualAttackClickButtonCombo.set('left')

    def getGameWindows(self) -> List[str]:
        def enum_windows_callback(hwnd: int, results: List[str]) -> None:
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if window_title:
                    results.append(window_title)

        results: List[str] = []
        win32gui.EnumWindows(enum_windows_callback, results)

        tibia_windows = [
            title for title in results
            if re.search(r"tibia", title, re.IGNORECASE)
            or re.search(r"windowed", title, re.IGNORECASE)
        ]

        return tibia_windows if tibia_windows else results

    def refreshWindows(self) -> None:
        self.windowsCombobox['values'] = self.getGameWindows()

    def onChangeWindow(self, _: Any) -> None:
        selectedWindow = self.windowsCombobox.get()
        if not self.context.setWindowTitle(selectedWindow):
            messagebox.showerror('Erro', 'Tibia window not found.')
        
    def onChangeShovelHotkey(self, event: Any) -> None:
        key = event.char
        key_pressed = event.keysym
        if key == '\b':
            return
        if re.match(r'^F[1-9]|1[0-2]$', key) or re.match(r'^[0-9]$', key) or re.match(r'^[a-z]$', key):
            self.shovelHotkeyEntry.delete(0, tk.END)
            self.context.setShovelHotkey(key)
        else:
            self.context.setShovelHotkey(key_pressed)
            self.shovelHotkeyEntryVar.set(key_pressed)

    def onChangeRopeHotkey(self, event: Any) -> None:
        key = event.char
        key_pressed = event.keysym
        if key == '\b':
            return
        if re.match(r'^F[1-9]|1[0-2]$', key) or re.match(r'^[0-9]$', key) or re.match(r'^[a-z]$', key):
            self.ropeHotkeyEntry.delete(0, tk.END)
            self.context.setRopeHotkey(key)
        else:
            self.context.setRopeHotkey(key_pressed)
            self.ropeHotkeyEntryVar.set(key_pressed)

    def onChangeAutoHurHotkey(self, event: Any) -> None:
        key = event.char
        key_pressed = event.keysym
        if key == '\b':
            return
        if re.match(r'^F[1-9]|1[0-2]$', key) or re.match(r'^[0-9]$', key) or re.match(r'^[a-z]$', key):
            self.autoHurHotkeyEntry.delete(0, tk.END)
            self.context.setAutoHurHotkey(key)
        else:
            self.context.setAutoHurHotkey(key_pressed)
            self.autoHurHotkeyEntryVar.set(key_pressed)

    def onToggleManualAutoAttack(self) -> None:
        enabled = bool(self.manualAttackEnabledVar.get())
        self.context.setManualAutoAttackEnabled(enabled)

    def onChangeManualAutoAttackHotkey(self, event: Any) -> None:
        key = event.char
        key_pressed = event.keysym
        if key == '\b':
            return

        # Normalize to a string that pyautogui understands (e.g. pageup, pagedown, f1, a, 1)
        if re.match(r'^F[1-9]|1[0-2]$', key) or re.match(r'^[0-9]$', key) or re.match(r'^[a-z]$', key):
            self.manualAttackHotkeyEntry.delete(0, tk.END)
            self.context.setManualAutoAttackHotkey(key)
        else:
            self.context.setManualAutoAttackHotkey(key_pressed)
            self.manualAttackHotkeyVar.set(key_pressed)

    def _updateManualAutoAttackIntervalLabel(self) -> None:
        try:
            v = float(self.manualAttackIntervalVar.get())
        except Exception:
            v = 0.70
        self.manualAttackIntervalValueLabel.configure(text=f"{v:.2f}")

    def onChangeManualAutoAttackInterval(self, _: Any = None) -> None:
        try:
            v = float(self.manualAttackIntervalVar.get())
        except Exception:
            v = 0.70
        self._updateManualAutoAttackIntervalLabel()
        self.context.setManualAutoAttackInterval(v)

    def onChangeManualAutoAttackMethod(self, _: Any = None) -> None:
        try:
            method = str(self.manualAttackMethodCombo.get()).strip().lower()
        except Exception:
            method = 'hotkey'
        self.context.setManualAutoAttackMethod(method)

    def onToggleManualAutoAttackOnlyWhenNotAttacking(self) -> None:
        self.context.setManualAutoAttackOnlyWhenNotAttacking(bool(self.manualAttackOnlyWhenNotAttackingVar.get()))

    def onToggleManualAutoAttackFocusBefore(self) -> None:
        self.context.setManualAutoAttackFocusBefore(bool(self.manualAttackFocusBeforeVar.get()))

    def onChangeManualAutoAttackKeyRepeat(self, _: Any = None) -> None:
        raw = ''
        try:
            raw = str(self.manualAttackKeyRepeatVar.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            repeats = int(raw)
        except Exception:
            repeats = 1
        self.context.setManualAutoAttackKeyRepeat(repeats)

    def onChangeManualAutoAttackPreDelay(self, _: Any = None) -> None:
        raw = ''
        try:
            raw = str(self.manualAttackPreDelayVar.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            v = float(raw)
        except Exception:
            v = 0.02
        self.context.setManualAutoAttackPreDelay(v)

    def onChangeManualAutoAttackFocusAfter(self, _: Any = None) -> None:
        raw = ''
        try:
            raw = str(self.manualAttackFocusAfterVar.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            v = float(raw)
        except Exception:
            v = 0.05
        self.context.setManualAutoAttackFocusAfter(v)

    def onChangeManualAutoAttackClickModifier(self, _: Any = None) -> None:
        try:
            mod = str(self.manualAttackClickModifierCombo.get()).strip().lower()
        except Exception:
            mod = 'none'
        self.context.setManualAutoAttackClickModifier(mod)

    def onChangeManualAutoAttackClickButton(self, _: Any = None) -> None:
        try:
            btn = str(self.manualAttackClickButtonCombo.get()).strip().lower()
        except Exception:
            btn = 'left'
        self.context.setManualAutoAttackClickButton(btn)

    def onToggleRuntimeAttackFromBattlelist(self) -> None:
        self.context.setRuntimeAttackFromBattlelist(bool(self.runtimeAttackFromBLVar.get()))

    def onToggleRuntimeTargetingDiag(self) -> None:
        self.context.setRuntimeTargetingDiag(bool(self.runtimeTargetingDiagVar.get()))

    def onToggleRuntimeWindowDiag(self) -> None:
        self.context.setRuntimeWindowDiag(bool(self.runtimeWindowDiagVar.get()))

    def onToggleRuntimeDumpTimeout(self) -> None:
        self.context.setRuntimeDumpTaskOnTimeout(bool(self.runtimeDumpTimeoutVar.get()))

    def onToggleRuntimeStartPaused(self) -> None:
        self.context.setRuntimeStartPaused(bool(self.runtimeStartPausedVar.get()))

    def onToggleRuntimeAttackOnly(self) -> None:
        self.context.setRuntimeAttackOnly(bool(self.runtimeAttackOnlyVar.get()))

    def onToggleRuntimeAllowAttackWithoutCoord(self) -> None:
        self.context.setRuntimeAllowAttackWithoutCoord(bool(self.runtimeAllowAttackWithoutCoordVar.get()))

    def onToggleRuntimeWarnOnWindowMiss(self) -> None:
        self.context.setRuntimeWarnOnWindowMiss(bool(self.runtimeWarnOnWindowMissVar.get()))

    def onChangeRuntimeStatusInterval(self, _: Any = None) -> None:
        raw = ''
        try:
            raw = str(self.runtimeStatusIntervalVar.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            v = float(raw)
        except Exception:
            v = 2.0
        self.context.setRuntimeStatusLogInterval(v)

    def onChangeRuntimeLootModifier(self, _: Any = None) -> None:
        try:
            mod = str(self.runtimeLootModifierCombo.get()).strip().lower()
        except Exception:
            mod = 'shift'
        self.context.setRuntimeLootModifier(mod)

    def onChangeRuntimeActionWindowTitle(self, _: Any = None) -> None:
        try:
            v = str(self.runtimeActionTitleVar.get())
        except Exception:
            v = ''
        self.context.setRuntimeActionWindowTitle(v)

    def onChangeRuntimeCaptureWindowTitle(self, _: Any = None) -> None:
        try:
            v = str(self.runtimeCaptureTitleVar.get())
        except Exception:
            v = ''
        self.context.setRuntimeCaptureWindowTitle(v)

    def onChangeRuntimeDepotOpenButton(self, _: Any = None) -> None:
        try:
            btn = str(self.runtimeDepotOpenButtonCombo.get()).strip().lower()
        except Exception:
            btn = 'right'
        self.context.setRuntimeDepotOpenButton(btn)

    def onChangeRuntimeAttackHotkey(self, _: Any = None) -> None:
        try:
            v = str(self.runtimeAttackHotkeyVar.get()).strip()
        except Exception:
            v = 'space'
        self.context.setRuntimeAttackHotkey(v)

    def onChangeRuntimeAttackClickButton(self, _: Any = None) -> None:
        try:
            btn = str(self.runtimeAttackClickButtonCombo.get()).strip().lower()
        except Exception:
            btn = 'left'
        self.context.setRuntimeAttackClickButton(btn)

    def onChangeRuntimeAttackSafeClickModifier(self, _: Any = None) -> None:
        try:
            mod = str(self.runtimeAttackSafeModifierCombo.get()).strip().lower()
        except Exception:
            mod = 'alt'
        self.context.setRuntimeAttackSafeClickModifier(mod)

    def onToggleRuntimeBlockRightClickAttack(self) -> None:
        self.context.setRuntimeBlockRightClickAttack(bool(self.runtimeBlockRightClickAttackVar.get()))

    def onChangeRuntimeAttackClickPreDelay(self, _: Any = None) -> None:
        raw = ''
        try:
            raw = str(self.runtimeAttackClickPreDelayVar.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            v = float(raw)
        except Exception:
            v = 0.06
        self.context.setRuntimeAttackClickPreDelay(v)

    def onChangeRuntimeBattlelistAttackClickModifier(self, _: Any = None) -> None:
        try:
            mod = str(self.runtimeBattlelistModifierCombo.get()).strip().lower()
        except Exception:
            mod = 'none'
        self.context.setRuntimeBattlelistAttackClickModifier(mod)

    def onChangeRuntimeBattlelistAttackClickButton(self, _: Any = None) -> None:
        try:
            btn = str(self.runtimeBattlelistButtonCombo.get()).strip().lower()
        except Exception:
            btn = 'left'
        self.context.setRuntimeBattlelistAttackClickButton(btn)

    def onToggleRuntimeBattlelistClickAtCursor(self) -> None:
        self.context.setRuntimeBattlelistClickAtCursor(bool(self.runtimeBattlelistClickAtCursorVar.get()))

    def onChangeRuntimeOutputIdx(self, _: Any = None) -> None:
        raw = ''
        try:
            raw = str(self.runtimeOutputIdxVar.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            v = int(float(raw))
        except Exception:
            v = 1
        self.context.setRuntimeOutputIdx(v)

    def onToggleRuntimeAutoOutputIdx(self) -> None:
        self.context.setRuntimeAutoOutputIdx(bool(self.runtimeAutoOutputIdxVar.get()))

    def onToggleRuntimeConsoleLog(self) -> None:
        self.context.setRuntimeConsoleLog(bool(self.runtimeConsoleLogVar.get()))

    def onChangeRuntimeLogLevel(self, _: Any = None) -> None:
        try:
            lvl = str(self.runtimeLogLevelCombo.get()).strip().lower()
        except Exception:
            lvl = 'info'
        self.context.setRuntimeLogLevel(lvl)

    def onToggleRuntimeSafeLog(self) -> None:
        self.context.setRuntimeSafeLog(bool(self.runtimeSafeLogVar.get()))

    def onToggleRuntimeInputDiag(self) -> None:
        self.context.setRuntimeInputDiag(bool(self.runtimeInputDiagVar.get()))

    def onToggleRuntimeDisableArduino(self) -> None:
        self.context.setRuntimeDisableArduino(bool(self.runtimeDisableArduinoVar.get()))

    def onToggleRuntimeDisableArduinoClicks(self) -> None:
        self.context.setRuntimeDisableArduinoClicks(bool(self.runtimeDisableArduinoClicksVar.get()))

    def onChangeRuntimeArduinoPort(self, _: Any = None) -> None:
        try:
            v = str(self.runtimeArduinoPortVar.get())
        except Exception:
            v = 'COM33'
        self.context.setRuntimeArduinoPort(v)

    def onChangeRuntimeTaskTimeout(self, task_key: str, _: Any = None) -> None:
        key = (task_key or '').strip()
        if not hasattr(self, 'runtimeTaskTimeoutVars'):
            return
        var = self.runtimeTaskTimeoutVars.get(key)
        if var is None:
            return
        raw = ''
        try:
            raw = str(var.get()).strip()
        except Exception:
            raw = ''
        if raw == '':
            return
        try:
            v = float(raw)
        except Exception:
            return
        self.context.setRuntimeTaskTimeout(key, v)

    def onResetRuntimeTaskTimeouts(self) -> None:
        specs = getattr(self, 'runtimeTaskTimeoutSpecs', None)
        vars_map = getattr(self, 'runtimeTaskTimeoutVars', None)
        if not isinstance(specs, list) or not isinstance(vars_map, dict):
            return
        for key, _label, default in specs:
            try:
                var = vars_map.get(key)
                if var is not None:
                    var.set(str(float(default)))
                self.context.setRuntimeTaskTimeout(str(key), float(default))
            except Exception:
                continue

    def onChangePoisonHotkey(self, event: Any) -> None:
        key = event.char
        key_pressed = event.keysym
        if key == '\b':
            return
        if re.match(r'^F[1-9]|1[0-2]$', key) or re.match(r'^[0-9]$', key) or re.match(r'^[a-z]$', key):
            self.poisonHotkeyEntry.delete(0, tk.END)
            self.context.setClearStatsPoisonHotkey(key)
        else:
            self.context.setClearStatsPoisonHotkey(key_pressed)
            self.poisonHotkeyEntryVar.set(key_pressed)

    def onToggleAutoHur(self) -> None:
        self.context.toggleAutoHur(self.checkVar.get())
        
    def onToggleAutoHurPz(self) -> None:
        self.context.toggleAutoHurPz(self.checkPzVar.get())

    def onToggleAlert(self) -> None:
        self.context.toggleAlert(self.alertCheckVar.get())
        
    def onToggleAlertCave(self) -> None:
        self.context.toggleAlertCave(self.alertCaveCheckVar.get())

    def onToggleAlertSayPlayer(self) -> None:
        self.context.toggleAlertSayPlayer(self.alertSayPlayerCheckVar.get())

    def onTogglePoison(self) -> None:
        self.context.toggleClearStatsPoison(self.checkPoisonVar.get())

    def setHurSpell(self, _: Any) -> None:
        self.context.setAutoHurSpell(self.hurSpellCombobox.get())

    def saveCfg(self) -> None:
        file = filedialog.asksaveasfilename(
            defaultextension=".pilotng",
            filetypes=[("PilotNG Cfg", "*.pilotng"), ("Todos os arquivos", "*.*")]
        )

        if file:
            cfg = {
                'ng_backpacks': self.context.context['ng_backpacks'],
                'general_hotkeys': self.context.context['general_hotkeys'],
                'auto_hur': self.context.context['auto_hur'],
                'alert': self.context.context['alert'],
                'clear_stats': self.context.context['clear_stats'],
                'manual_auto_attack': self.context.context.get('manual_auto_attack', {}),
                'ng_runtime': self.context.context.get('ng_runtime', {}),
                'ng_comboSpells': self.context.context['ng_comboSpells'],
                'healing': self.context.context['healing']
            }
            with open(file, 'w') as f:
                json.dump(cfg, f, indent=4)
            messagebox.showinfo('Sucesso', 'Cfg salva com sucesso!')

    def loadCfg(self) -> None:
        file = filedialog.askopenfilename(
            defaultextension=".pilotng",
            filetypes=[
                ("PilotNG Cfg", "*.pilotng"),
                ("Setup JSON", "*.json"),
                ("Todos os arquivos", "*.*"),
            ]
        )

        if file:
            with open(file, 'r') as f:
                cfg = json.load(f)
                # Support both the native .pilotng schema and legacy scripts-master setup_*.json files.
                if isinstance(cfg, dict) and 'ng_backpacks' in cfg and 'healing' in cfg:
                    self.context.loadCfg(cfg)
                elif isinstance(cfg, dict) and 'hunt_config' in cfg and 'items' in cfg:
                    # Legacy setup JSON (scripts-master).
                    self.context.importLegacySetup(cfg)
                else:
                    messagebox.showerror('Erro', 'Formato de configuração não suportado (esperado .pilotng ou setup_*.json).')
                    return
            messagebox.showinfo('Sucesso', 'Cfg carregada com sucesso!')