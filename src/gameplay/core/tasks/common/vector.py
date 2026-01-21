from ....typings import Context
from .base import BaseTask


class VectorTask(BaseTask):
    def __init__(self, name: str = 'vectorTask') -> None:
        super().__init__(name=name)
        self.currentTaskIndex = 0
        self.tasks: list[BaseTask] = []

    def shouldRestartAfterAllChildrensComplete(self, _: Context) -> bool:
        return False
