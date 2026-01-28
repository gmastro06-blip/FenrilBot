import src.repositories.refill.core as refillCore
import src.utils.mouse as mouse
from ...typings import Context
from .common.base import BaseTask


# TODO: check if npc tradebox was closed
class CloseNpcTradeBoxTask(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'closeNpcTradeBox'
        self.delayBeforeStart = 1
        self.delayAfterComplete = 0.5

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        screenshot = context['ng_screenshot']
        tradeTopPosition = refillCore.getTradeTopPosition(screenshot)
        
        if tradeTopPosition is not None:
            # UI antigua detectada
            mouse.leftClick((tradeTopPosition[0] + 165, tradeTopPosition[1] + 7))
        else:
            # Intentar cerrar la UI moderna
            from src.repositories.refill.modern_ui import closeModernTradeWindow
            closeModernTradeWindow(screenshot)
        
        return context
