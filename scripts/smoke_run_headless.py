"""Headless smoke-run for PilotNG loop.

Runs the gameplay thread without launching the CustomTkinter UI.
Intended to validate capture + middlewares + task scheduling end-to-end.

Safety:
- Set FENRIL_DISABLE_INPUT=1 to ensure no mouse/keyboard is sent.
- You can always abort with ESC (global kill switch).

Example (PowerShell):
  $env:FENRIL_CAPTURE_BACKEND='obsws'
  $env:FENRIL_OBS_SOURCE='Tibia_Fuente'
  $env:FENRIL_OBS_HOST='127.0.0.1'
  $env:FENRIL_OBS_PORT='4455'
  $env:FENRIL_DISABLE_INPUT='1'
  $env:FENRIL_START_PAUSED='0'
  python scripts/smoke_run_headless.py --seconds 15
"""

from __future__ import annotations

import argparse
import sys
import time
from threading import Thread
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Headless smoke-run for Fenril/PilotNG")
    parser.add_argument("--seconds", type=float, default=15.0, help="How long to run the mainloop")
    args = parser.parse_args()

    # Ensure repo root on path
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from src.gameplay.context import context as base_context
    from src.gameplay.threads.pilotNG import PilotNGThread
    from src.ui.context import Context
    from src.utils.esc_stop import install_esc_stop

    ctx = Context(base_context)
    install_esc_stop(ctx, exit_process=True)

    # Force unpaused for this smoke run.
    ctx.context["ng_pause"] = False

    thread = PilotNGThread(ctx)
    t = Thread(target=thread.mainloop, daemon=True)
    t.start()

    started = time.time()
    last_print = 0.0

    while True:
        now = time.time()
        if now - started >= float(args.seconds):
            break
        if not t.is_alive():
            break
        if now - last_print >= 1.0:
            last_print = now
            dbg: Any = ctx.context.get("ng_debug")
            diag: Any = ctx.context.get("ng_diag")
            last_exc = None
            last_reason = None
            if isinstance(dbg, dict):
                last_exc = dbg.get("last_exception")
                last_reason = dbg.get("last_tick_reason")
            cap_mean = None
            cap_std = None
            backend = None
            if isinstance(diag, dict):
                cap_mean = diag.get("capture_mean")
                cap_std = diag.get("capture_std")
            try:
                from src.utils.core import getScreenshotDebugInfo

                backend = (getScreenshotDebugInfo().get("last_stats") or {}).get("backend")
            except Exception:
                backend = None

            print(
                f"[smoke] alive={t.is_alive()} backend={backend} reason={last_reason} "
                f"capture_mean={cap_mean} capture_std={cap_std} last_exception={last_exc}"
            )

        time.sleep(0.05)

    # Stop
    ctx.context["ng_should_stop"] = True
    try:
        t.join(timeout=2.0)
    except Exception:
        pass

    dbg: Any = ctx.context.get("ng_debug")
    last_exc = None
    if isinstance(dbg, dict):
        last_exc = dbg.get("last_exception")

    if last_exc:
        print(f"[smoke] FAIL last_exception={last_exc}")
        return 1

    if not t.is_alive():
        print("[smoke] OK (thread exited)")
    else:
        print("[smoke] OK (thread stopped request sent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
