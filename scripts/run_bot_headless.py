"""Run Fenril bot without the CustomTkinter UI.

This is intended for live validation and long-running sessions where the UI window
isn't needed (or tends to be closed/minimized).

Stop conditions:
- Press ESC anytime (global emergency stop).
- Ctrl+C in the terminal.

Notes:
- Respect existing env vars like FENRIL_CAPTURE_BACKEND/FENRIL_OBS_*.
- Use FENRIL_START_PAUSED=1 if you want to start paused.
- Use FENRIL_DISABLE_INPUT=1 for safe dry-runs.
"""

from __future__ import annotations

import argparse
import sys
import time
from threading import Thread
from typing import Any


def _ensure_repo_root_on_path() -> None:
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Fenril bot without the UI")
    parser.add_argument(
        "--seconds",
        type=float,
        default=0.0,
        help="If > 0, run for N seconds then stop (useful for testing).",
    )
    args = parser.parse_args()

    _ensure_repo_root_on_path()

    from src.gameplay.context import context as base_context
    from src.gameplay.threads.alert import AlertThread
    from src.gameplay.threads.pilotNG import PilotNGThread
    from src.ui.context import Context
    from src.utils.esc_stop import install_esc_stop

    ctx = Context(base_context)

    # ESC should terminate the entire process in headless mode.
    install_esc_stop(ctx, exit_process=True)

    alert_thread = AlertThread(ctx)
    alert_thread.start()

    pilot = PilotNGThread(ctx)

    print("[headless] started (press ESC to stop)")

    thread: Thread | None = None
    try:
        if float(args.seconds) > 0:
            thread = Thread(target=pilot.mainloop, daemon=True)
            thread.start()

            deadline = time.time() + float(args.seconds)
            while time.time() < deadline and thread.is_alive():
                time.sleep(0.05)

            ctx.context["ng_should_stop"] = True
            try:
                thread.join(timeout=2.0)
            except Exception:
                pass
        else:
            pilot.mainloop()
    except KeyboardInterrupt:
        print("[headless] Ctrl+C received; stopping...")
        ctx.context["ng_should_stop"] = True
        return 0
    except SystemExit:
        # ESC stop uses SystemExit when exit_process=True
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"[headless] ERROR: {exc!r}")
        ctx.context["ng_should_stop"] = True
        # Give threads a moment to observe stop request.
        time.sleep(0.2)
        return 1
    finally:
        # If PilotNG exits normally, also request stop.
        ctx.context["ng_should_stop"] = True

    # If we ever return here, emit a small summary.
    dbg: Any = ctx.context.get("ng_debug")
    last_exc = None
    last_reason = None
    if isinstance(dbg, dict):
        last_exc = dbg.get("last_exception")
        last_reason = dbg.get("last_tick_reason")

    if last_exc:
        print(f"[headless] stopped with last_exception={last_exc}")
        return 1

    print(f"[headless] stopped (last_reason={last_reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
