from src.gameplay.typings import Context
from src.repositories.chat.core import getChatStatus
import src.utils.keyboard as keyboard
from .common.base import BaseTask


# TODO: check if chat is off on did
class SetChatOffTask(BaseTask):
    def __init__(self: "SetChatOffTask") -> None:
        super().__init__()
        self.name = 'setChatOff'
        self.delayBeforeStart = 0.5
        self.delayAfterComplete = 0.5

    # TODO: add unit tests
    def shouldIgnore(self, context: Context) -> bool:
        if context.get('ng_screenshot') is None:
            return False
        (_, chatIsOn) = getChatStatus(context['ng_screenshot'])
        return not chatIsOn

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        keyboard.press('enter')
        return context
