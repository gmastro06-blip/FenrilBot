from ...typings import Context
from .common.vector import VectorTask
from .enableChat import EnableChatTask
from .say import SayTask
from .selectChatTab import SelectChatTabTask


class SayPlayerAfterBoxTask(VectorTask):
    def __init__(self: "SayPlayerAfterBoxTask") -> None:
        super().__init__()
        self.isRootTask = True
        self.name = 'sayPlayerAfterBox'

    # TODO: add unit tests
    def onBeforeStart(self, context: Context) -> Context:
        if context['gameWindow']['players'] and context['alert']['sayPlayer'] is True:
            self.tasks = [
                SelectChatTabTask('local chat').setParentTask(self).setRootTask(self),
                EnableChatTask().setParentTask(self).setRootTask(self),
                SayTask('?').setParentTask(self).setRootTask(self),
            ]
        return context


# Backwards-compatible alias (older code imported the lowercase name).
sayPlayerAfterBoxTask = SayPlayerAfterBoxTask
