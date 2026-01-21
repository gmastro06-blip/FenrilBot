import base64
import os
from time import sleep

from typing import Optional

import serial

_arduinoSerial = None
_arduinoAvailable = None


def _is_clickish_command(command: str) -> bool:
    c = command.strip()
    if c in {"leftClick", "rightClick", "dragStart", "dragEnd"}:
        return True
    if c.startswith("scroll,"):
        return True
    return False


def _getArduinoPort() -> str:
    return os.getenv("FENRIL_ARDUINO_PORT", "COM33")


def _ensureArduinoSerial() -> Optional[serial.Serial]:
    global _arduinoSerial, _arduinoAvailable
    if _arduinoAvailable is False:
        return None
    if _arduinoSerial is not None:
        return _arduinoSerial

    try:
        _arduinoSerial = serial.Serial(_getArduinoPort(), 115200, timeout=1)
        _arduinoAvailable = True
        return _arduinoSerial
    except Exception:
        _arduinoAvailable = False
        _arduinoSerial = None
        return None


def sendCommandArduino(command: str) -> bool:
    if os.getenv('FENRIL_DISABLE_ARDUINO', '0') in {'1', 'true', 'True'}:
        return False

    # Some Arduino firmwares apply smoothing/delays that make clicks appear to "not happen".
    # Allow bypassing Arduino for click-like commands while still using Arduino for moveTo.
    if os.getenv('FENRIL_DISABLE_ARDUINO_CLICKS', '0') in {'1', 'true', 'True'} and _is_clickish_command(command):
        return False
    arduinoSerial = _ensureArduinoSerial()
    if arduinoSerial is None:
        return False

    try:
        commandBytes = command.encode("utf-8")
        commandBase64 = base64.b64encode(commandBytes).decode("utf-8") + "\n"
        arduinoSerial.write(commandBase64.encode())
        sleep(0.01)
        return True
    except Exception:
        global _arduinoAvailable, _arduinoSerial
        _arduinoAvailable = False
        _arduinoSerial = None
        return False