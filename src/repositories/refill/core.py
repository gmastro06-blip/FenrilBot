from time import sleep
from typing import Optional
from src.shared.typings import BBox, GrayImage
from src.utils.core import cacheObjectPosition, locate, locateMultiScale, getScreenshot
from src.utils.image import crop
from src.utils.keyboard import hotkey, press, write
from src.utils.mouse import leftClick, moveTo
from .config import images, npcTradeBarImages, npcTradeOkImages


def _locate_any_template(
    screenshot: GrayImage,
    templates: list[GrayImage],
    *,
    confidence: float,
    scales: tuple[float, ...],
) -> Optional[BBox]:
    for template in templates:
        pos = locateMultiScale(
            screenshot,
            template,
            confidence=confidence,
            scales=scales,
        )
        if pos is not None:
            return pos
    for template in templates:
        pos = locate(screenshot, template, confidence=confidence)
        if pos is not None:
            return pos
    return None


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getTradeTopPosition(screenshot: GrayImage) -> Optional[BBox]:
    # Robust to capture scaling/DPI.
    # If you always capture at native 1920x1080 with 100% scaling, this behaves the same.
    return _locate_any_template(
        screenshot,
        npcTradeBarImages,
        confidence=0.80,
        scales=(0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25),
    )


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getTradeBottomPos(screenshot: GrayImage) -> Optional[BBox]:
    tradeTopPos = getTradeTopPosition(screenshot)
    if tradeTopPos is None:
        return None
    (x, y, _, _) = tradeTopPos
    # The legacy trade window width is ~174px, but user-captured OK templates may be wider.
    # Widen the search crop to avoid matchTemplate failures and increase robustness.
    crop_width = 174
    try:
        for tpl in npcTradeOkImages:
            try:
                w = int(tpl.shape[1])
            except Exception:
                continue
            crop_width = max(crop_width, w + 20)
    except Exception:
        pass
    croppedImage = crop(screenshot, x, y, crop_width, len(screenshot) - y)
    tradeOkPos = _locate_any_template(
        croppedImage,
        npcTradeOkImages,
        confidence=0.80,
        scales=(0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25),
    )
    if tradeOkPos is None:
        return None
    (_, botY, _, _) = tradeOkPos
    return x, y + botY + 26, 174, 2


# TODO: add unit tests
# TODO: add perf
def findItem(screenshot: GrayImage, itemName: str) -> None:
    tradeBottomPos = getTradeBottomPos(screenshot)
    if tradeBottomPos is None:
        return
    (bx, by, _, _) = tradeBottomPos
    leftClick((bx + 160, by - 75))
    sleep(0.2)
    leftClick((bx + 16, by - 75))
    sleep(0.2)
    write(itemName)
    sleep(2)
    screenshotAfterFind = getScreenshot()
    if screenshotAfterFind is None:
        return
    itemImg = images[itemName]
    itemPos = locate(screenshotAfterFind, itemImg)
    if itemPos is None:
        return
    # TODO: improve it, click should be done in a handle coordinate inside the box
    x = itemPos[0] + 10
    y = itemPos[1] + 10
    leftClick((x, y))


# TODO: add unit tests
# TODO: add perf
def setAmount(screenshot: GrayImage, amount: int) -> None:
    tradeBottomPos = getTradeBottomPos(screenshot)
    if tradeBottomPos is None:
        return
    (bx, by, _, _) = tradeBottomPos
    leftClick((bx + 115, by - 42))
    sleep(0.2)
    hotkey('ctrl', 'a')
    sleep(0.2)
    press('backspace')
    write(str(amount))


# TODO: add unit tests
# TODO: add perf
def confirmBuyItem(screenshot: GrayImage) -> None:
    tradeBottomPos = getTradeBottomPos(screenshot)
    if tradeBottomPos is None:
        return
    (bx, by, _, _) = tradeBottomPos
    leftClick((bx + 150, by - 18))


# TODO: add unit tests
# TODO: add perf
def clearSearchBox(screenshot: GrayImage) -> None:
    tradeBottomPos = getTradeBottomPos(screenshot)
    if tradeBottomPos is None:
        return
    (bx, by, _, _) = tradeBottomPos
    x = bx + 115 + 45
    y = by - 42 - 35
    moveTo((x, y))
    leftClick((x, y))
    moveTo((x, y + 20))


# TODO: add unit tests
# TODO: add perf
def buyItem(screenshot: GrayImage, itemName: str, itemQuantity: int) -> None:
    findItem(screenshot, itemName)
    sleep(1)
    setAmount(screenshot, itemQuantity)
    sleep(1)
    confirmBuyItem(screenshot)
    sleep(1)
    clearSearchBox(screenshot)
    sleep(1)
