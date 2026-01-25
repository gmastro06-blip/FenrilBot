from time import time
import json
import os
import pathlib
from datetime import datetime
from typing import Any

import cv2
import numpy as np
from typing import Optional

from src.gameplay.typings import Context
from .common.base import BaseTask
from .common.vector import VectorTask
from src.utils.runtime_settings import get_bool


class TasksOrchestrator:
    def __init__(self) -> None:
        self.rootTask: Optional[BaseTask] = None

    # TODO: add unit tests
    def setRootTask(self, context: Context, task: BaseTask) -> None:
        currentTask = self.getCurrentTask(context)
        if currentTask is not None:
            self.interruptTasks(context, currentTask)
        if task is not None:
            task.isRootTask = True
        self.rootTask = task

    # TODO: add unit tests
    def interruptTasks(self, context: Context, task: BaseTask) -> Context:
        context = task.onInterrupt(context)
        if task.parentTask is not None:
            return self.interruptTasks(context, task.parentTask)
        return context

    # TODO: add unit tests
    def reset(self) -> None:
        self.rootTask = None
        # terminate all tasks in the tree

    def getCurrentTask(self, context: Context) -> Optional[BaseTask]:
        return self.getNestedTask(self.rootTask, context)

    def getCurrentTaskName(self, context: Context) -> str:
        currentTask = self.getNestedTask(self.rootTask, context)
        if currentTask is None:
            return 'unknown'
        if currentTask.isRootTask:
            return currentTask.name
        return currentTask.rootTask.name if currentTask.rootTask is not None else currentTask.name

    def getNestedTask(self, task: Optional[BaseTask], context: Context) -> Optional[BaseTask]:
        if task is None:
            return None
        if isinstance(task, VectorTask):
            if task.status == 'notStarted':
                if task.startedAt is None:
                    task.startedAt = time()
                try:
                    context = task.applyRuntimeConfig(context)
                except Exception:
                    pass
                context = task.onBeforeStart(context)
                task.status = 'running'
            if task.status != 'completed':
                if len(task.tasks) == 0:
                    return task
                return self.getNestedTask(task.tasks[task.currentTaskIndex], context)
        return task

    # TODO: add unit tests
    def do(self, context: Context) -> Context:
        currentTask = self.getCurrentTask(context)
        self.checkHooks(currentTask, context)
        return self.handleTasks(context)

    def checkHooks(self, currentTask: Optional[BaseTask], context: Context) -> Context:
        if currentTask is not None and currentTask.manuallyTerminable and currentTask.shouldManuallyComplete(context):
            currentTask.status = 'completed'
            currentTask.statusReason = 'completed'
            return self.markCurrentTaskAsFinished(currentTask, context, disableManualTermination=True)
        if currentTask is not None and currentTask.status != 'notStarted' and currentTask.shouldRestart(context):
            currentTask.status = 'notStarted'
            currentTask.retryCount += 1
            if isinstance(currentTask, VectorTask):
                currentTask.currentTaskIndex = 0
            context = currentTask.onBeforeRestart(context)
        if currentTask is not None and currentTask.parentTask:
            self.checkHooks(currentTask.parentTask, context)
        return context

    def handleTasks(self, context: Context) -> Context:
        if self.rootTask is None:
            return context
        if self.rootTask.status == 'completed':
            return context
        currentTask = self.getCurrentTask(context)

        # Root-task timeouts: VectorTask roots were previously never timing out
        # because VectorTask.start logic bypassed handleTasks' startedAt setup.
        # Check the root timer as a guardrail for long-running task trees.
        if currentTask is not None:
            root = getattr(currentTask, 'rootTask', None)
            if root is not None and root is not currentTask and root.status != 'completed':
                if self.didTaskTimedout(root):
                    self._maybe_dump_timeout(context, root)
                    context = root.onTimeout(context)
                    currentTask.statusReason = 'timeout'
                    return self.markCurrentTaskAsFinished(
                        currentTask,
                        context,
                        shouldTimeoutTreeWhenTimeout=True,
                    )

        if currentTask is not None and currentTask.status == 'awaitingManualTermination':
            if currentTask.shouldManuallyComplete(context):
                currentTask.status = 'completed'
                currentTask.statusReason = 'completed'
                return self.markCurrentTaskAsFinished(currentTask, context, disableManualTermination=True)
            if currentTask.shouldRestart(context) and currentTask.isRestarting == False:
                currentTask.startedAt = None
                currentTask.status = 'notStarted'
                currentTask.isRestarting = True
                currentTask.retryCount += 1
                return currentTask.onBeforeRestart(context)
            return context
        if currentTask is not None and (currentTask.status == 'notStarted' or currentTask.status == 'awaitingDelayBeforeStart'):
            currentTask.isRestarting = False
            if currentTask.startedAt is None:
                currentTask.startedAt = time()
            try:
                context = currentTask.applyRuntimeConfig(context)
            except Exception:
                pass
            context = currentTask.onBeforeStart(context)
            if self.didPassedEnoughTimeToExecute(currentTask):
                if currentTask.shouldIgnore(context):
                    context = currentTask.onIgnored(context)
                    return self.markCurrentTaskAsFinished(currentTask, context)
                else:
                    currentTask.status = 'running'
                    return currentTask.do(context)
            else:
                currentTask.status = 'awaitingDelayBeforeStart'
            return context
        elif currentTask is not None and currentTask.status == 'running':
            # IMPORTANT: even "non-terminable" tasks must be able to timeout.
            # Otherwise tasks like drag/scroll loops can stall the entire bot forever.
            if not currentTask.terminable:
                if self.didTaskTimedout(currentTask):
                    self._maybe_dump_timeout(context, currentTask)
                    context = currentTask.onTimeout(context)
                    currentTask.statusReason = 'timeout'
                    return self.markCurrentTaskAsFinished(
                        currentTask,
                        context,
                        shouldTimeoutTreeWhenTimeout=currentTask.shouldTimeoutTreeWhenTimeout,
                    )
                context = currentTask.ping(context)
                return currentTask.do(context)
            if currentTask.shouldRestart(context):
                currentTask.status = 'notStarted'
                return context
            else:
                if self.didTaskTimedout(currentTask):
                    self._maybe_dump_timeout(context, currentTask)
                    context = currentTask.onTimeout(context)
                    currentTask.statusReason = 'timeout'
                    return self.markCurrentTaskAsFinished(currentTask, context, shouldTimeoutTreeWhenTimeout=currentTask.shouldTimeoutTreeWhenTimeout)
                if currentTask.did(context):
                    currentTask.finishedAt = time()
                    if currentTask.delayAfterComplete > 0:
                        currentTask.status = 'awaitingDelayToComplete'
                        return context
                    else:
                        return self.markCurrentTaskAsFinished(currentTask, context)
                else:
                    context = currentTask.ping(context)
        if currentTask is not None and currentTask.status == 'awaitingDelayToComplete' and self.didPassedEnoughDelayAfterTaskComplete(currentTask):
            return self.markCurrentTaskAsFinished(currentTask, context)
        return context

    def _maybe_dump_timeout(self, context: Context, task: BaseTask) -> None:
        if not get_bool(context, 'ng_runtime.dump_task_on_timeout', env_var='FENRIL_DUMP_TASK_ON_TIMEOUT', default=False):
            return
        screenshot = context.get('ng_screenshot') if isinstance(context, dict) else None
        if screenshot is None:
            return
        try:
            debug_dir = pathlib.Path('debug')
            debug_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            name = getattr(task, 'name', 'unknown')

            img_path = debug_dir / f'task_timeout_{name}_{ts}.png'
            meta_path = debug_dir / f'task_timeout_{name}_{ts}.json'

            cv2.imwrite(str(img_path), np.ascontiguousarray(screenshot))

            meta: dict[str, Any] = {
                'task': {
                    'name': name,
                    'status': getattr(task, 'status', None),
                    'statusReason': getattr(task, 'statusReason', None),
                    'startedAt': getattr(task, 'startedAt', None),
                    'delayOfTimeout': getattr(task, 'delayOfTimeout', None),
                    'retryCount': getattr(task, 'retryCount', None),
                    'terminable': getattr(task, 'terminable', None),
                    'rootTask': getattr(getattr(task, 'rootTask', None), 'name', None),
                    'parentTask': getattr(getattr(task, 'parentTask', None), 'name', None),
                },
                'window': {
                    'action_title': context.get('ng_window', {}).get('action_title'),
                    'capture_title': context.get('ng_window', {}).get('capture_title'),
                    'capture_rect': context.get('ng_capture_rect'),
                    'action_rect': context.get('ng_action_rect'),
                },
                'waypoints': {
                    'currentIndex': context.get('ng_cave', {}).get('waypoints', {}).get('currentIndex'),
                    'currentType': None,
                },
                'radar': {
                    'coordinate': context.get('ng_radar', {}).get('coordinate'),
                },
                'battleList': {
                    'count': None,
                },
            }
            try:
                items = context.get('ng_cave', {}).get('waypoints', {}).get('items')
                idx = context.get('ng_cave', {}).get('waypoints', {}).get('currentIndex')
                if isinstance(items, list) and isinstance(idx, int) and 0 <= idx < len(items):
                    meta['waypoints']['currentType'] = items[idx].get('type')
            except Exception:
                pass
            try:
                creatures = context.get('ng_battleList', {}).get('creatures')
                meta['battleList']['count'] = len(creatures) if creatures is not None else None
            except Exception:
                pass

            meta_path.write_text(json.dumps(meta, indent=2), encoding='utf-8')
        except Exception:
            # Never let diagnostics break the main loop.
            return

    # TODO: add unit tests
    def markCurrentTaskAsFinished(self, task: BaseTask, context: Context, disableManualTermination: bool = False, shouldTimeoutTreeWhenTimeout: bool = False) -> Context:
        if task.manuallyTerminable and disableManualTermination == False:
            task.status = 'awaitingManualTermination'
            return context
        else:
            task.status = 'completed'
            if task.statusReason is None:
                task.statusReason = 'timeout' if shouldTimeoutTreeWhenTimeout else 'completed'
        context = task.onComplete(context)
        if task.parentTask:
            if shouldTimeoutTreeWhenTimeout:
                context = task.parentTask.onTimeout(context)
                context = self.markCurrentTaskAsFinished(
                    task.parentTask, context, shouldTimeoutTreeWhenTimeout=shouldTimeoutTreeWhenTimeout)
                return context
            if isinstance(task.parentTask, VectorTask):
                if task.parentTask.currentTaskIndex < len(task.parentTask.tasks) - 1:
                    task.parentTask.currentTaskIndex += 1
                else:
                    if task.parentTask.shouldRestartAfterAllChildrensComplete(context):
                        task.parentTask.status = 'notStarted'
                        task.parentTask.currentTaskIndex = 0
                        task.parentTask.retryCount += 1
                        return task.parentTask.onBeforeRestart(context)
                    context = self.markCurrentTaskAsFinished(task.parentTask, context)
        return context

    def didPassedEnoughTimeToExecute(self, task: BaseTask) -> bool:
        if task.startedAt is None:
            return False
        return time() - task.startedAt >= task.delayBeforeStart

    def didPassedEnoughDelayAfterTaskComplete(self, task: BaseTask) -> bool:
        if task.finishedAt is None:
            return False
        return time() - task.finishedAt >= task.delayAfterComplete

    def didTaskTimedout(self, task: BaseTask) -> bool:
        if task.startedAt is None:
            return False
        return task.delayOfTimeout > 0 and time() - task.startedAt >= task.delayOfTimeout
