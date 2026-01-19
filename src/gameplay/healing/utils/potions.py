# TODO: add typings
# TODO: add unit tests
from typing import Optional

from src.utils.safety import safe_int


def matchHpHealing(healing: dict, statusBar: Optional[dict]) -> bool:
    if statusBar is None:
        return False
    hp_percentage = safe_int(statusBar.get('hpPercentage'), label="hpPercentage")
    mana_percentage = safe_int(statusBar.get('manaPercentage'), label="manaPercentage")
    hp_limit = safe_int(healing.get('hpPercentageLessThanOrEqual'), label="hpLimit")
    mana_min = safe_int(healing.get('manaPercentageGreaterThanOrEqual'), label="manaMin")
    if hp_percentage is None:
        return False
    if hp_limit is not None and hp_percentage > hp_limit:
        return False
    if mana_min is not None and mana_percentage is not None and mana_percentage < mana_min:
        return False
    return True


# TODO: add typings
# TODO: add unit tests
def matchManaHealing(healing: dict, statusBar: Optional[dict]) -> bool:
    if statusBar is None:
        return False
    mana_percentage = safe_int(statusBar.get('manaPercentage'), label="manaPercentage")
    mana_limit = safe_int(healing.get('manaPercentageLessThanOrEqual'), label="manaLimit")
    if mana_percentage is None or mana_limit is None:
        return False
    if mana_percentage > mana_limit:
        return False
    return True