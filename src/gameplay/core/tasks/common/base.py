from __future__ import annotations

from time import time
from typing import Optional

from src.gameplay.typings import Context


class BaseTask:
    def __init__(
        self,
        delayBeforeStart: float = 0,
        delayAfterComplete: float = 0,
        delayOfTimeout: float = 0,
        isRootTask: bool = False,
        manuallyTerminable: bool = False,
        name: str = 'baseTask',
        parentTask: Optional[BaseTask] = None,
        shouldTimeoutTreeWhenTimeout: bool = False,
    ) -> None:
        self.createdAt = time()
        self.startedAt: Optional[float] = None
        self.finishedAt: Optional[float] = None
        self.isRestarting: bool = False
        self.terminable = True
        self.delayBeforeStart = delayBeforeStart
        self.delayAfterComplete = delayAfterComplete
        self.delayOfTimeout = delayOfTimeout
        self.isRetrying = False
        self.isRootTask = isRootTask
        self.manuallyTerminable = manuallyTerminable
        self.name = name
        self.parentTask: Optional[BaseTask] = parentTask
        self.retryCount = 0
        self.rootTask: Optional[BaseTask] = None
        self.shouldTimeoutTreeWhenTimeout = shouldTimeoutTreeWhenTimeout
        self.status = 'notStarted'
        self.statusReason: Optional[str] = None

    def setParentTask(self, parentTask: Optional[BaseTask]) -> BaseTask:
        self.parentTask = parentTask
        return self

    def setRootTask(self, rootTask: Optional[BaseTask]) -> BaseTask:
        self.rootTask = rootTask
        return self

    def shouldIgnore(self, _: Context) -> bool:
        return False

    def shouldManuallyComplete(self, _: Context) -> bool:
        return False

    def shouldRestart(self, _: Context) -> bool:
        return False

    def do(self, context: Context) -> Context:
        return context

    def did(self, _: Context) -> bool:
        return True

    def ping(self, context: Context) -> Context:
        return context

    def onBeforeStart(self, context: Context) -> Context:
        return context

    def onBeforeRestart(self, context: Context) -> Context:
        return context

    def onIgnored(self, context: Context) -> Context:
        return context

    def onInterrupt(self, context: Context) -> Context:
        return context

    def onComplete(self, context: Context) -> Context:
        return context

    def onTimeout(self, context: Context) -> Context:
        return context
