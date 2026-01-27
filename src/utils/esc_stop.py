from __future__ import annotations

import os
import threading
import time
from typing import Any, Optional


_STOP_EVENT = threading.Event()
_INSTALLED = False
_INSTALL_LOCK = threading.Lock()


def _is_esc_pressed() -> bool:
    """Best-effort global ESC detection.

    On Windows, uses GetAsyncKeyState so it works even when Tibia is focused.
    """
    try:
        # Windows-only; avoid adding new dependencies.
        import ctypes  # type: ignore

        VK_ESCAPE = 0x1B
        state = ctypes.windll.user32.GetAsyncKeyState(VK_ESCAPE)
        return bool(state & 0x8000)
    except Exception:
        return False


def _mark_context_should_stop(context_holder: Any) -> None:
    """Set stop flags in either a UI Context or a plain dict."""
    try:
        ctx = getattr(context_holder, "context", None)
        if isinstance(ctx, dict):
            ctx["ng_should_stop"] = True
            ctx["ng_pause"] = True
            return
    except Exception:
        pass

    if isinstance(context_holder, dict):
        context_holder["ng_should_stop"] = True
        context_holder["ng_pause"] = True


def install_esc_stop(
    context_holder: Optional[Any] = None,
    *,
    exit_process: bool = False,
    poll_interval_s: float = 0.05,
) -> threading.Event:
    """Install a global ESC listener.

    - If context_holder is provided, sets `ng_should_stop=1` and `ng_pause=1`.
    - If exit_process=True, terminates the process immediately via os._exit(0).

    Returns a threading.Event that becomes set once ESC is detected.
    """
    global _INSTALLED
    with _INSTALL_LOCK:
        if _INSTALLED:
            return _STOP_EVENT
        _INSTALLED = True

    def _loop() -> None:
        while not _STOP_EVENT.is_set():
            if _is_esc_pressed():
                _STOP_EVENT.set()
                try:
                    if context_holder is not None:
                        _mark_context_should_stop(context_holder)
                except Exception:
                    pass

                if exit_process:
                    # Immediate, reliable stop for diagnostics/preflight runs.
                    # (Thread-safe exit; avoids hanging in sleeps or OpenCV calls.)
                    os._exit(0)
                return

            time.sleep(max(0.01, float(poll_interval_s)))

    t = threading.Thread(target=_loop, name="esc-stop", daemon=True)
    t.start()
    return _STOP_EVENT
