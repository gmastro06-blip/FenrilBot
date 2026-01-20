import customtkinter
from tkinter import messagebox
from typing import Any, Callable, Mapping, Optional

from src.ui.utils import genRanStr


def _noop_on_confirm(_label: Optional[str], _payload: dict) -> None:
    return None

class BuyBackpackModal(customtkinter.CTkToplevel):
    def __init__(
        self,
        parent: Any,
        onConfirm: Callable[[Optional[str], dict], Any] = _noop_on_confirm,
        waypoint: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(parent)
        self.onConfirm = onConfirm

        self.title(genRanStr())
        self.resizable(False, False)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.buyBackpackFrame = customtkinter.CTkFrame(self)
        self.buyBackpackFrame.grid(column=0, row=1, padx=(10, 5),
                                    pady=(10, 0), sticky='nsew')
        self.buyBackpackFrame.rowconfigure(0, weight=1)
        self.buyBackpackFrame.rowconfigure(1, weight=1)

        self.backpackCombobox = customtkinter.CTkComboBox(
            self.buyBackpackFrame, values=['Orange Backpack', 'Red Backpack', 'Parcel'], state='readonly')
        self.backpackCombobox.grid(
            row=0, column=0, sticky='nsew', padx=10, pady=10)
        if waypoint is not None:
            options = waypoint.get('options') if hasattr(waypoint, 'get') else None
            backpackItem = (options or {}).get(
                'name', 'Orange Backpack')
            self.backpackCombobox.set(backpackItem)

        self.backpackAmountEntry = customtkinter.CTkEntry(
            self.buyBackpackFrame,
            validate='key',
            validatecommand=(self.register(self.validateNumber), "%P"),
        )
        self.backpackAmountEntry.grid(
            row=1, column=0, sticky='nsew', padx=10, pady=10)
        if waypoint is not None:
            backpackAmount = str(
                ((options or {}).get('amount', 12)))
            self.backpackAmountEntry.insert(0, backpackAmount)

        self.confirmButton = customtkinter.CTkButton(
            self, text='Confirm', command=self.confirm,
            corner_radius=32, fg_color="transparent", border_color="#C20034",
            border_width=2, hover_color="#C20034")
        self.confirmButton.grid(
            row=2, column=0, padx=10, pady=10, sticky='nsew')

        self.cancelButton = customtkinter.CTkButton(
            self, text='Cancel', command=self.destroy,
            corner_radius=32, fg_color="transparent", border_color="#C20034",
            border_width=2, hover_color="#C20034")
        self.cancelButton.grid(
            row=2, column=1, padx=10, pady=10, sticky='nsew')

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
            'name': self.backpackCombobox.get(),
            'amount': int(self.backpackAmountEntry.get())
        })
        self.destroy()
