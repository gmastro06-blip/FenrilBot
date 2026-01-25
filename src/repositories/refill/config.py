import glob
import os
import pathlib
from typing import Optional

import numpy as np
from src.utils.image import loadFromRGBToGray

from src.shared.typings import GrayImage


currentPath = pathlib.Path(__file__).parent.resolve()

# Baseline templates (repo defaults).
npcTradeBarImage = np.asarray(
    loadFromRGBToGray(f'{currentPath}/images/npcTradeBar.png'), dtype=np.uint8
)
npcTradeOkImage = np.asarray(
    loadFromRGBToGray(f'{currentPath}/images/npcTradeOk.png'), dtype=np.uint8
)


def _load_optional_gray(path: str) -> Optional[GrayImage]:
    try:
        return loadFromRGBToGray(path)
    except Exception:
        return None


def _load_optional_glob_gray(pattern: str) -> list[GrayImage]:
    out: list[GrayImage] = []
    for fp in sorted(glob.glob(pattern)):
        img = _load_optional_gray(fp)
        if img is not None:
            out.append(np.asarray(img, dtype=np.uint8))
    return out


tradeTabsPath = os.path.join(str(currentPath), 'images', 'tradeTabs')

# Optional: alternate NPC trade window templates.
# Use these when your client UI differs (theme/DPI/capture scaling) from the repo defaults.
# Add files like:
# - src/repositories/refill/images/npcTradeBar_user.png
# - src/repositories/refill/images/npcTradeOk_user.png
npcTradeBarImages: list[GrayImage] = [
    npcTradeBarImage,
    *_load_optional_glob_gray(os.path.join(str(currentPath), 'images', 'npcTradeBar_*.png')),
]
npcTradeOkImages: list[GrayImage] = [
    npcTradeOkImage,
    *_load_optional_glob_gray(os.path.join(str(currentPath), 'images', 'npcTradeOk_*.png')),
]

# Optional: buy/sell tab templates for the newer NPC trade UI.
# Users can add files like:
# - src/repositories/refill/images/tradeTabs/buy.png
# - src/repositories/refill/images/tradeTabs/sell.png
# or multiple variants (buy_*.png / sell_*.png).
tradeTabsImages = {
    'buy': _load_optional_glob_gray(os.path.join(tradeTabsPath, 'buy*.png')),
    'sell': _load_optional_glob_gray(os.path.join(tradeTabsPath, 'sell*.png')),
}

images = {
    'Parcel': loadFromRGBToGray(f'{currentPath}/images/potions/parcel.png'),
    'Orange Backpack': loadFromRGBToGray(f'{currentPath}/images/potions/orangeBackpack.png'),
    'Red Backpack': loadFromRGBToGray(f'{currentPath}/images/potions/redBackpack.png'),
    'Great Health Potion': loadFromRGBToGray(f'{currentPath}/images/potions/greatHealthPotion.png'),
    'Great Mana Potion': loadFromRGBToGray(f'{currentPath}/images/potions/greatManaPotion.png'),
    'Great spirit Potion': loadFromRGBToGray(f'{currentPath}/images/potions/greatSpiritPotion.png'),
    'Health Potion': loadFromRGBToGray(f'{currentPath}/images/potions/healthPotion.png'),
    'Mana Potion': loadFromRGBToGray(f'{currentPath}/images/potions/manaPotion.png'),
    'Strong Health Potion': loadFromRGBToGray(f'{currentPath}/images/potions/strongHealthPotion.png'),
    'Strong Mana Potion': loadFromRGBToGray(f'{currentPath}/images/potions/strongManaPotion.png'),
    'Supreme Health Potion': loadFromRGBToGray(f'{currentPath}/images/potions/supremeHealthPotion.png'),
    'Ultimate Health Potion': loadFromRGBToGray(f'{currentPath}/images/potions/ultimateHealthPotion.png'),
    'Ultimate Mana Potion': loadFromRGBToGray(f'{currentPath}/images/potions/ultimateManaPotion.png'),
    'Ultimate Spirit Potion': loadFromRGBToGray(f'{currentPath}/images/potions/ultimateSpiritPotion.png'),
}
