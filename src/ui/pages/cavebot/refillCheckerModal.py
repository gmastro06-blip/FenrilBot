from tkinter import messagebox, BooleanVar
import customtkinter
from typing import Any, Callable, Mapping, Optional, Sequence

from src.ui.utils import genRanStr


def _noop_on_confirm(_label: Optional[str], _payload: dict) -> None:
    return None


def _safe_positive_int(value: str) -> int:
    value = value.strip()
    if not value.isdigit():
        return 0
    parsed = int(value)
    return parsed if parsed > 0 else 0

class RefillCheckerModal(customtkinter.CTkToplevel):
    def __init__(
        self,
        parent: Any,
        onConfirm: Callable[[Optional[str], dict], Any] = _noop_on_confirm,
        waypoint: Optional[Mapping[str, Any]] = None,
        waypointsLabels: Optional[Sequence[str]] = None,
    ) -> None:
        super().__init__(parent)
        self.onConfirm = onConfirm

        self.title(genRanStr())
        self.resizable(False, False)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.frame = customtkinter.CTkFrame(self)
        self.frame.grid(column=0, row=1, columnspan=2, padx=10,
                        pady=10, sticky='nsew')
        self.frame.rowconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self.healthEnabledVar = BooleanVar()
        if waypoint is not None:
            options = waypoint.get('options')
            healthEnabled = (options or {}).get('healthEnabled')
            if healthEnabled is not None:
                self.healthEnabledVar.set(healthEnabled)
        self.healthEnabledButton = customtkinter.CTkCheckBox(
            self.frame, text='Check Health', variable=self.healthEnabledVar,
            hover_color="#870125", fg_color='#C20034')
        self.healthEnabledButton.grid(column=0, row=0, padx=10, pady=10, sticky='w')

        self.minimumOfHealthPotionLabel = customtkinter.CTkLabel(
            self.frame, text='Health Potion:', anchor='w')
        self.minimumOfHealthPotionLabel.grid(
            row=1, column=0, sticky='nsew', padx=10, pady=(10, 0))

        self.minimumAmountOfHealthPotionsEntry = customtkinter.CTkEntry(self.frame, validate='key',
                                                        validatecommand=(self.register(self.validateNumber), "%P"))
        self.minimumAmountOfHealthPotionsEntry.grid(
            row=2, column=0, sticky='nsew', padx=10, pady=10)
        if waypoint is not None:
            self.minimumAmountOfHealthPotionsEntry.insert(
                0, str((options or {}).get('minimumAmountOfHealthPotions')))

        self.minimumOfManaPotionLabel = customtkinter.CTkLabel(
            self.frame, text='Mana Potion:', anchor='w')
        self.minimumOfManaPotionLabel.grid(
            row=3, column=0, sticky='nsew', padx=10, pady=(10, 0))

        self.minimumAmountOfManaPotionsEntry = customtkinter.CTkEntry(self.frame, validate='key',
                                                        validatecommand=(self.register(self.validateNumber), "%P"))
        self.minimumAmountOfManaPotionsEntry.grid(
            row=4, column=0, sticky='nsew', padx=10, pady=10)
        if waypoint is not None:
            self.minimumAmountOfManaPotionsEntry.insert(
                0, str((options or {}).get('minimumAmountOfManaPotions')))

        self.minimumOfCapLabel = customtkinter.CTkLabel(
            self.frame, text='Cap:', anchor='w')
        self.minimumOfCapLabel.grid(
            row=5, column=0, sticky='nsew', padx=10, pady=(10, 0))

        self.minimumAmountOfCapEntry = customtkinter.CTkEntry(self.frame, validate='key',
                                                validatecommand=(self.register(self.validateNumber), "%P"))
        self.minimumAmountOfCapEntry.grid(
            row=6, column=0, sticky='nsew', padx=10, pady=10)
        if waypoint is not None:
            self.minimumAmountOfCapEntry.insert(
                0, str((options or {}).get('minimumAmountOfCap')))

        self.waypointLabelToRedirectLabel = customtkinter.CTkLabel(
            self.frame, text='Go to label:', anchor='w')
        self.waypointLabelToRedirectLabel.grid(
            row=7, column=0, sticky='nsew', padx=10, pady=(10, 0))

        labels = list(waypointsLabels) if waypointsLabels is not None else []
        self.waypointLabelToRedirectCombobox = customtkinter.CTkComboBox(
            self.frame, values=labels, state='readonly')
        self.waypointLabelToRedirectCombobox.grid(
            row=8, column=0, sticky='nsew', padx=10, pady=10)
        if waypoint is not None:
            label_to_redirect = (options or {}).get('waypointLabelToRedirect')
            if label_to_redirect:
                self.waypointLabelToRedirectCombobox.set(str(label_to_redirect))

        self.confirmButton = customtkinter.CTkButton(
            self, text='Confirm', command=self.confirm,
            corner_radius=32, fg_color="transparent", border_color="#C20034",
            border_width=2, hover_color="#C20034")
        self.confirmButton.grid(
            row=7, column=0, padx=(10, 5), pady=(5, 10), sticky='nsew')

        self.cancelButton = customtkinter.CTkButton(
            self, text='Cancel', command=self.destroy,
            corner_radius=32, fg_color="transparent", border_color="#C20034",
            border_width=2, hover_color="#C20034")
        self.cancelButton.grid(
            row=7, column=1, padx=(5, 10), pady=(5, 10), sticky='nsew')

    def validateNumber(self, value: str) -> bool:
        if value == '':
            return True
        if value.isdigit() and int(value) > 0:
            return True
        messagebox.showerror(
            'Error', "Digite um número válido maior que zero.")
        return False

    def confirm(self) -> None:
        self.onConfirm(None, {
            'minimumAmountOfHealthPotions': _safe_positive_int(self.minimumAmountOfHealthPotionsEntry.get()),
            'minimumAmountOfManaPotions': _safe_positive_int(self.minimumAmountOfManaPotionsEntry.get()),
            'minimumAmountOfCap': _safe_positive_int(self.minimumAmountOfCapEntry.get()),
            'waypointLabelToRedirect': self.waypointLabelToRedirectCombobox.get(),
            'healthEnabled': self.healthEnabledVar.get(),
        })
        self.destroy()
