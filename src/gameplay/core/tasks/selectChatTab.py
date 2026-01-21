from src.gameplay.typings import Context
from src.utils.mouse import leftClick
from .common.base import BaseTask


# TODO: implement should ignore if tab already selected
class SelectChatTabTask(BaseTask):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = 'selectChatTab'
        self.delayBeforeStart = 0.5
        self.delayAfterComplete = 0.5
        self.tabName = name

    # TODO: add unit tests
    def shouldIgnore(self, context: Context) -> bool:
        tabs = context.get('ng_chat', {}).get('tabs') if isinstance(context, dict) else None
        if not isinstance(tabs, dict):
            return False
        tab = tabs.get(self.tabName)
        if tab is None:
            return False
        return tab['isSelected']

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        tabs = context.get('ng_chat', {}).get('tabs') if isinstance(context, dict) else None
        if not isinstance(tabs, dict):
            return context
        tab = tabs.get(self.tabName)
        if not isinstance(tab, dict):
            return context
        tabPosition = tab.get('position')
        if not isinstance(tabPosition, (list, tuple)) or len(tabPosition) < 2:
            return context
        # TODO: implement random click in BBox
        leftClick((tabPosition[0] + 10, tabPosition[1] + 5))
        return context
