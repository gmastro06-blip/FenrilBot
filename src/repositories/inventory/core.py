from src.shared.typings import GrayImage
from src.utils.core import locate, locateMultiScale
from .config import images


# TODO: add unit tests
# TODO: add perf
def isContainerOpen(screenshot: GrayImage, name: str) -> bool:
    if not name:
        return False

    # Support template variants without changing configured backpack names.
    # Example: user can add `Camouflage Backpack v2.png` to containersBars/ and it will be tried too.
    candidate_names = [name]
    try:
        candidate_names.extend(
            [
                k
                for k in images.get('containersBars', {}).keys()
                if isinstance(k, str) and k != name and k.startswith(name + ' ')
            ]
        )
    except Exception:
        pass

    templates = []
    for cand in candidate_names:
        try:
            templates.append(images['containersBars'][cand])
        except Exception:
            continue

    if not templates:
        return False

    for tpl in templates:
        # Fast path: exact-scale match.
        if locate(screenshot, tpl) is not None:
            return True

        # Fallback: OBS projector / DPI scaling slightly resizes UI.
        if (
            locateMultiScale(
                screenshot,
                tpl,
                confidence=0.78,
                scales=(0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20),
            )
            is not None
        ):
            return True

    return False
