from src.gameplay.typings import Context
import src.repositories.chat.core as chatCore
import src.utils.keyboard as keyboard
from .common.base import BaseTask


# TODO: check if chat is off on did
class EnableChatTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'enableChat'
        self.delayBeforeStart = 2
        self.delayAfterComplete = 2

    def shouldIgnore(self, context: Context) -> bool:
        if context.get('ng_screenshot') is None:
            return False
        (_, chatIsOn) = chatCore.getChatStatus(context['ng_screenshot'])
        return chatIsOn

    def do(self, context: Context) -> Context:
        keyboard.press('enter')
        return context
