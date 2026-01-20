from threading import Thread
from typing import Any

from src.ui.application import Application


class UIThread(Thread):
    # TODO: add typings
    def __init__(self, context: Any) -> None:
        super().__init__()
        self.context = context

    def run(self) -> None:
        app = Application(self.context)
        app.mainloop()
