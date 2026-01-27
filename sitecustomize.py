"""Repo-wide Python hook.

Python automatically imports `sitecustomize` on startup (when present on sys.path).
This lets us install global safety features for *any* script/test started from the repo.

Emergency stop:
- Press ESC anytime to abort the current Python process.
"""

from __future__ import annotations


def _install() -> None:
    try:
        # Default to hard-exit so it can stop even if the code is stuck in a click loop.
        from src.utils.esc_stop import install_esc_stop

        install_esc_stop(exit_process=True)
    except Exception:
        # Never break startup.
        return


_install()
