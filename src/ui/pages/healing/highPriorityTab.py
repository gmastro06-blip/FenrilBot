from .healthFoodCard import HealthFoodCard
from .manaFoodCard import ManaFoodCard
from .swapAmuletCard import SwapAmuletCard
from .swapRingCard import SwapRingCard
import customtkinter
import tkinter as tk
from typing import Any


class HighPriorityTab(customtkinter.CTkFrame):
    def __init__(self, parent: tk.Misc, context: Any) -> None:
        super().__init__(parent)
        self.context = context
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.healthFoodCard = HealthFoodCard(self, context)
        self.healthFoodCard.grid(column=0, row=0, padx=10,
                                pady=10, sticky='nsew')

        self.manaFoodCard = ManaFoodCard(self, context)
        self.manaFoodCard.grid(column=1, row=0, padx=10,
                            pady=10, sticky='nsew')

        self.swapRingCard = SwapRingCard(self, context)
        self.swapRingCard.grid(column=0, row=1, padx=10,
                            pady=10, sticky='nsew')

        self.swapAmuletCard = SwapAmuletCard(self, context)
        self.swapAmuletCard.grid(column=1, row=1, padx=10,
                                pady=10, sticky='nsew')
