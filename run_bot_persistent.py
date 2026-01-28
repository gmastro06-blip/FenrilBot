"""
Persistent bot runner - keeps the bot running even if the GUI closes unexpectedly.
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
    contextInstance = Context(context)
    # Emergency stop: press ESC anytime to stop the bot.
    install_esc_stop(contextInstance, exit_process=True)
    # Toggle pause/play: press INSERT anytime to toggle bot state.
    install_insert_toggle(contextInstance)
    alertThreadInstance = AlertThread(contextInstance)
    alertThreadInstance.start()
    pilotNGThreadInstance = PilotNGThread(contextInstance)
    pilotThread = Thread(target=pilotNGThreadInstance.mainloop, daemon=True)
    pilotThread.start()
    
    print("[run_bot_persistent] Bot threads started. Press ESC to stop.")
    print("[run_bot_persistent] Bot running without GUI (headless mode)")
    print("[run_bot_persistent] Press INSERT to toggle pause/play")
    
    try:
        # Keep main thread alive without GUI
        while not contextInstance.context.get('ng_should_stop', False):
            time.sleep(1)
    except KeyboardInterrupt:
        print("[run_bot_persistent] Ctrl+C detected, stopping...")
        contextInstance.context['ng_should_stop'] = True
    
    print("[run_bot_persistent] Bot stopped.")

if __name__ == '__main__':
    main()
