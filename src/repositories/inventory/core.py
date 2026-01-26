from src.shared.typings import GrayImage
from src.utils.core import locate, locateMultiScale
from .config import images


# TODO: add unit tests
# TODO: add perf
def isContainerOpen(screenshot: GrayImage, name: str) -> bool:
    try:
        tpl = images['containersBars'][name]
    except Exception:
        return False

    # Fast path: exact-scale match.
    if locate(screenshot, tpl) is not None:
        return True

    # Fallback: OBS projector / DPI scaling slightly resizes UI.
    return (
        locateMultiScale(
            screenshot,
            tpl,
            confidence=0.78,
            scales=(0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20),
        )
        is not None
    )
