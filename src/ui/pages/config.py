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
                'ng_comboSpells': self.context.context['ng_comboSpells'],
                'healing': self.context.context['healing']
            }
            with open(file, 'w') as f:
                json.dump(cfg, f, indent=4)
            messagebox.showinfo('Sucesso', 'Cfg salva com sucesso!')

    def loadCfg(self) -> None:
        file = filedialog.askopenfilename(
            defaultextension=".pilotng",
            filetypes=[("PilotNG Cfg", "*.pilotng"), ("Todos os arquivos", "*.*")]
        )

        if file:
            with open(file, 'r') as f:
                cfg = json.load(f)
                self.context.loadCfg(cfg)
            messagebox.showinfo('Sucesso', 'Cfg carregada com sucesso!')