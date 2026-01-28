"""
Bot runner with forced initial coordinate.
This bypasses radar matching and starts tracking from a known position.
"""
import sys
import time
from threading import Thread

from src.gameplay.context import context
from src.gameplay.threads.pilotNG import PilotNGThread
from src.gameplay.threads.alert import AlertThread
from src.ui.context import Context
from src.utils.esc_stop import install_esc_stop
from src.utils.insert_toggle import install_insert_toggle

def main() -> None:
    # Force initial coordinate (Ab'dendriel depot)
    INITIAL_COORD = (32679, 31687, 6)
    
    contextInstance = Context(context)
    
    # Set initial coordinate directly
    print(f"[run_bot_with_coord] Setting initial coordinate: {INITIAL_COORD}")
    contextInstance.context['coordinate'] = INITIAL_COORD
    contextInstance.context['last_coord_time'] = time.time()
    
    # Emergency stop: press ESC anytime to stop the bot.
    install_esc_stop(contextInstance, exit_process=True)
    # Toggle pause/play: press INSERT anytime to toggle bot state.
    install_insert_toggle(contextInstance)
    
    alertThreadInstance = AlertThread(contextInstance)
    alertThreadInstance.start()
    pilotNGThreadInstance = PilotNGThread(contextInstance)
    pilotThread = Thread(target=pilotNGThreadInstance.mainloop, daemon=True)
    pilotThread.start()
    
    print("[run_bot_with_coord] Bot threads started. Press ESC to stop.")
    print("[run_bot_with_coord] Bot running without GUI (headless mode)")
    print("[run_bot_with_coord] Press INSERT to toggle pause/play")
    print(f"[run_bot_with_coord] Starting from: {INITIAL_COORD}")
    
    try:
        # Keep main thread alive without GUI
        while not contextInstance.context.get('ng_should_stop', False):
            time.sleep(1)
    except KeyboardInterrupt:
        print("[run_bot_with_coord] Ctrl+C detected, stopping...")
        contextInstance.context['ng_should_stop'] = True
    
    print("[run_bot_with_coord] Bot stopped.")

if __name__ == '__main__':
    main()
