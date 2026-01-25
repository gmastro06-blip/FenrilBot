import base64
from time import sleep

from typing import Any, Optional

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None  # type: ignore

from src.utils.runtime_settings import get_bool, get_str

_arduinoSerial: Optional[Any] = None
_arduinoAvailable = None

_ARDUINO_PORT: str = get_str({}, '_', env_var='FENRIL_ARDUINO_PORT', default='COM33', prefer_env=True)
_DISABLE_ARDUINO: bool = get_bool({}, '_', env_var='FENRIL_DISABLE_ARDUINO', default=False, prefer_env=True)
_DISABLE_ARDUINO_CLICKS: bool = get_bool({}, '_', env_var='FENRIL_DISABLE_ARDUINO_CLICKS', default=False, prefer_env=True)


def configure_arduino(
    *,
    port: Optional[str] = None,
    disable_arduino: Optional[bool] = None,
    disable_clicks: Optional[bool] = None,
) -> None:
    """Configure Arduino input backend.

    Defaults come from env vars, but runtime can override via profile config.
    """
    global _ARDUINO_PORT, _DISABLE_ARDUINO, _DISABLE_ARDUINO_CLICKS, _arduinoSerial, _arduinoAvailable
    if port is not None:
        p = str(port).strip()
        if p:
            _ARDUINO_PORT = p
            # Force re-open with new port on next use.
            _arduinoSerial = None
            _arduinoAvailable = None
    if disable_arduino is not None:
        _DISABLE_ARDUINO = bool(disable_arduino)
    if disable_clicks is not None:
        _DISABLE_ARDUINO_CLICKS = bool(disable_clicks)


def _is_clickish_command(command: str) -> bool:
    c = command.strip()
    if c in {"leftClick", "rightClick", "dragStart", "dragEnd"}:
        return True
    if c.startswith("scroll,"):
        return True
    return False


def _getArduinoPort() -> str:
    return _ARDUINO_PORT


def _ensureArduinoSerial() -> Optional[Any]:
    global _arduinoSerial, _arduinoAvailable
    if _arduinoAvailable is False:
        return None
    if _arduinoSerial is not None:
        return _arduinoSerial

    if serial is None:
        _arduinoAvailable = False
        _arduinoSerial = None
        return None

    try:
        _arduinoSerial = serial.Serial(_getArduinoPort(), 115200, timeout=1)
        _arduinoAvailable = True
        return _arduinoSerial
    except Exception:
        _arduinoAvailable = False
        _arduinoSerial = None
        return None


def sendCommandArduino(command: str) -> bool:
    if _DISABLE_ARDUINO:
        return False

    # Some Arduino firmwares apply smoothing/delays that make clicks appear to "not happen".
    # Allow bypassing Arduino for click-like commands while still using Arduino for moveTo.
    if _DISABLE_ARDUINO_CLICKS and _is_clickish_command(command):
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