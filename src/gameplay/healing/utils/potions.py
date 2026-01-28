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
    
    # ERROR 4 FIXED: Validar hp_percentage no es None
    if hp_percentage is None:
        return False
    
    # ERROR 4 FIXED: Si hay límite de HP, solo curar si está por debajo o igual
    if hp_limit is not None and hp_percentage > hp_limit:
        return False
    
    # Validar requisito de mana mínima (si está configurado)
    if mana_min is not None:
        if mana_percentage is None or mana_percentage < mana_min:
            return False
    
    return True


# TODO: add typings
# TODO: add unit tests
def matchManaHealing(healing: dict, statusBar: Optional[dict]) -> bool:
    if statusBar is None:
        return False
    mana_percentage = safe_int(statusBar.get('manaPercentage'), label="manaPercentage")
    mana_limit = safe_int(healing.get('manaPercentageLessThanOrEqual'), label="manaLimit")
    
    # ERROR 5 FIXED: Validar ambos valores antes de comparar
    if mana_percentage is None or mana_limit is None:
        return False
    
    # Solo curar mana si está por debajo o igual al límite configurado
    if mana_percentage > mana_limit:
        return False
    
    return True