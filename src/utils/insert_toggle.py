from __future__ import annotations

import threading
import time
from typing import Any, Optional

from src.utils.console_log import log


_INSTALLED = False
_INSTALL_LOCK = threading.Lock()
_LAST_INSERT_STATE = False


def _is_insert_pressed() -> bool:
    """Global INSERT detection on Windows using GetAsyncKeyState."""
    try:
        import ctypes  # type: ignore

        VK_INSERT = 0x2D  # Virtual key code for INSERT
        state = ctypes.windll.user32.GetAsyncKeyState(VK_INSERT)
        return bool(state & 0x8000)
    except Exception:
        return False


def _toggle_pause(context_holder: Any) -> None:
    """Toggle ng_pause state in either a UI Context or a plain dict."""
    try:
        ctx = getattr(context_holder, "context", None)
        if isinstance(ctx, dict):
            current = ctx.get("ng_pause", True)
            ctx["ng_pause"] = not current
            new_state = "PAUSED" if ctx["ng_pause"] else "PLAYING"
            log('info', f"INSERT pressed - Bot {new_state}")
            return
    except Exception:
        pass

    if isinstance(context_holder, dict):
        current = context_holder.get("ng_pause", True)
        context_holder["ng_pause"] = not current
        new_state = "PAUSED" if context_holder["ng_pause"] else "PLAYING"
        log('info', f"INSERT pressed - Bot {new_state}")


def install_insert_toggle(
    context_holder: Optional[Any] = None,
    *,
    poll_interval_s: float = 0.05,
) -> None:
    """Install a global INSERT listener to toggle pause/play.

    - If context_holder is provided, toggles `ng_pause` between True/False.
    - Only triggers on key press (not on key hold).
    """
    global _INSTALLED
    with _INSTALL_LOCK:
        if _INSTALLED:
            return
        _INSTALLED = True

    def _loop() -> None:
        global _LAST_INSERT_STATE
        while True:
            current_state = _is_insert_pressed()
            
            # Detect rising edge (key was released, now pressed)
            if current_state and not _LAST_INSERT_STATE:
                try:
                    if context_holder is not None:
                        _toggle_pause(context_holder)
                except Exception:
                    pass
            
            _LAST_INSERT_STATE = current_state
            time.sleep(max(0.01, float(poll_interval_s)))

    t = threading.Thread(target=_loop, name="insert-toggle", daemon=True)
    t.start()
