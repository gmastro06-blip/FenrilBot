import pathlib
from typing import Any, Dict, List, Optional, Tuple, Union
from src.shared.typings import BBox, GrayImage
from src.repositories.gameWindow.core import getLeftArrowPosition
from src.utils.core import cacheObjectPosition, hashit, locate, locateMultiScale, locateMultiple
from src.utils.image import convertGraysToBlack, loadFromRGBToGray
from .config import hashes


currentPath = pathlib.Path(__file__).parent.resolve()
chatMenuImg = loadFromRGBToGray(f'{currentPath}/images/chatMenu.png')
chatOnImg = loadFromRGBToGray(f'{currentPath}/images/chatOn.png')
chatOnImgTemp = loadFromRGBToGray(f'{currentPath}/images/chatOnTemp.png')
chatOffImg = loadFromRGBToGray(f'{currentPath}/images/chatOff.png')
chatOffImg = loadFromRGBToGray(f'{currentPath}/images/chatOff.png')
lootOfTextImg = loadFromRGBToGray(f'{currentPath}/images/lootOfText.png')
nothingTextImg = loadFromRGBToGray(f'{currentPath}/images/nothingText.png')
oldListOfLootCheck: List[int] = []


# TODO: add unit tests
# TODO: add perf
# TODO: add tests
def getTabs(screenshot: GrayImage) -> Dict[str, Dict[str, Any]]:
    shouldFindTabs = True
    tabIndex = 0
    tabs: Dict[str, Dict[str, Any]] = {}
    leftSidebarArrowsPosition = getLeftArrowPosition(screenshot)
    chatMenuPosition = getChatMenuPosition(screenshot)
    if leftSidebarArrowsPosition is not None and chatMenuPosition is not None:
        x, y, width, height = leftSidebarArrowsPosition[0] + 18, chatMenuPosition[1], chatMenuPosition[0] - (
            leftSidebarArrowsPosition[0] + 18), 20
        if width <= 0 or height <= 0:
            return {}
        chatsTabsContainerImage = screenshot[y:y + height, x:x + width]
        if chatsTabsContainerImage.size == 0:
            return {}
        while shouldFindTabs:
            xOfTab = tabIndex * 96
            if xOfTab < 0 or xOfTab >= chatsTabsContainerImage.shape[1]:
                break
            firstPixel = chatsTabsContainerImage[0, xOfTab]
            # Older code relied on exact pixel values (114/125) which breaks under
            # capture scaling, UI themes, or minor gamma changes. Use a tolerance.
            if int(firstPixel) < 80 or int(firstPixel) > 170:
                shouldFindTabs = False
                continue
            tabImage = chatsTabsContainerImage[2:16, xOfTab + 2:xOfTab + 2 + 92]
            if tabImage.size == 0:
                break
            tabName = hashes['tabs'].get(hashit(tabImage), 'Unknown')
            if tabName != 'Unknown':
                tabs.setdefault(
                    tabName, {'isSelected': int(firstPixel) <= 120, 'position': (x + xOfTab, y, 92, 14)})
            tabIndex += 1
        return tabs
    else:
        return {}


# TODO: add unit tests
# TODO: add perf
def hasNewLoot(screenshot: GrayImage) -> bool:
    global oldListOfLootCheck
    lootLines = getLootLines(screenshot)
    if len(lootLines) == 0:
        return False
    listOfLootCheck = []
    start = 5
    if len(lootLines) - 5 <= 0:
        start = len(lootLines)
    for i in range(len(lootLines) - start, len(lootLines)):
        listOfLootCheck.append(hashit(
            convertGraysToBlack(lootLines[i][0])))
    if len(listOfLootCheck) != 0 and len(oldListOfLootCheck) == 0:
        oldListOfLootCheck = listOfLootCheck
        return True
    for newLootLine in listOfLootCheck:
        if newLootLine not in oldListOfLootCheck:
            oldListOfLootCheck = listOfLootCheck
            return True
    oldListOfLootCheck = listOfLootCheck
    return False

def resetOldList() -> None:
    global oldListOfLootCheck
    oldListOfLootCheck = []

# TODO: add unit tests
# TODO: add perf
def getLootLines(screenshot: GrayImage) -> List[Tuple[GrayImage, BBox]]:
    messageContainerPosition = getChatMessagesContainerPosition(screenshot)
    if messageContainerPosition is None:
        return []
    (x, y, w, h) = messageContainerPosition
    messages = screenshot[y: y + h, x: x + w]
    lootLines = locateMultiple(lootOfTextImg, messages)
    linesWithLoot = []
    for line in lootLines:
        line = x, line[1] + y, w, line[3]
        lineImg = screenshot[line[1]:line[1] +
                            line[3], line[0]:line[0] + line[2]]
        nothingFound = locate(nothingTextImg, lineImg)
        if nothingFound is None:
            linesWithLoot.append((lineImg, line))
    return linesWithLoot


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getChatMenuPosition(screenshot: GrayImage) -> Union[BBox, None]:
    # OBS projector + Windows DPI scaling can slightly resize the capture output.
    # Use multiscale matching so chat-dependent features (loot detection, tab clicks)
    # keep working.
    return locateMultiScale(
        screenshot,
        chatMenuImg,
        confidence=0.78,
        scales=(0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20),
    )


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getChatOffPosition(screenshot: GrayImage) -> Union[BBox, None]:
    return locateMultiScale(
        screenshot,
        chatOffImg,
        confidence=0.92,
        scales=(0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15),
    )


# TODO: add unit tests
# TODO: add perf
def getChatStatus(screenshot: GrayImage) -> Tuple[Optional[BBox], bool]:
    # TODO: chat off/on pos is always the same. Get it by hash
    chatOffPos = getChatOffPosition(screenshot)
    if chatOffPos:
        return chatOffPos, False
    chatOnPos = locateMultiScale(
        screenshot,
        chatOnImgTemp,
        confidence=0.80,
        scales=(0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15),
    )
    return chatOnPos, True


# TODO: add unit tests
# TODO: add perf
@cacheObjectPosition
def getChatMessagesContainerPosition(screenshot: GrayImage) -> Optional[BBox]:
    leftSidebarArrows = getLeftArrowPosition(screenshot)
    chatMenu = getChatMenuPosition(screenshot)
    chatStatus = getChatStatus(screenshot)
    if leftSidebarArrows is not None and all(leftSidebarArrows) \
        and chatMenu is not None and all(chatMenu) \
        and chatStatus is not None and chatStatus[0] is not None:
        return leftSidebarArrows[0] + 5, chatMenu[1] + 18, chatStatus[0][0] + 40, (chatStatus[0][1] - 6) - (chatMenu[1] + 13)
    else:
        return None
