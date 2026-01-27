from threading import Thread

from src.gameplay.context import context
from src.gameplay.threads.pilotNG import PilotNGThread
from src.gameplay.threads.alert import AlertThread
from src.ui.application import Application
from src.ui.context import Context
from src.utils.esc_stop import install_esc_stop

def main() -> None:
    contextInstance = Context(context)
    # Emergency stop: press ESC anytime to stop the bot.
    install_esc_stop(contextInstance, exit_process=False)
    alertThreadInstance = AlertThread(contextInstance)
    alertThreadInstance.start()
    pilotNGThreadInstance = PilotNGThread(contextInstance)
    pilotThread = Thread(target=pilotNGThreadInstance.mainloop, daemon=True)
    pilotThread.start()
    app = Application(contextInstance)
    app.mainloop()

if __name__ == '__main__':
    main()
