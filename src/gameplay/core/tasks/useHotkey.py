from src.utils.keyboard import press
from ...typings import Context
from .common.base import BaseTask


class UseHotkeyTask(BaseTask):
    def __init__(self: "UseHotkeyTask", hotkey: str, delayAfterComplete: float = 1) -> None:
        super().__init__()
        self.name = 'useHotkey'
        self.delayAfterComplete = delayAfterComplete
        self.hotkey = hotkey

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        press(self.hotkey)
        return context
