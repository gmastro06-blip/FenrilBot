from threading import Thread

from src.gameplay.context import context
from src.gameplay.threads.pilotNG import PilotNGThread
from src.gameplay.threads.alert import AlertThread
from src.ui.application import Application
from src.ui.context import Context

def main() -> None:
    contextInstance = Context(context)
    alertThreadInstance = AlertThread(contextInstance)
    alertThreadInstance.start()
    pilotNGThreadInstance = PilotNGThread(contextInstance)
    pilotThread = Thread(target=pilotNGThreadInstance.mainloop, daemon=True)
    pilotThread.start()
    app = Application(contextInstance)
    app.mainloop()

if __name__ == '__main__':
    main()
