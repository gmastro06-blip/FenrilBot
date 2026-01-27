import pathlib
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
from src.shared.typings import BBox, GrayImage
from src.repositories.gameWindow.core import getLeftArrowPosition
from src.utils.core import cacheObjectPosition, hashit, locate, locateMultiScale, locateMultiple
from src.utils.image import convertGraysToBlack, loadFromRGBToGray
from src.utils.runtime_settings import get_bool
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


def _chat_scale_from_menu(chat_menu_bbox: Optional[BBox]) -> float:
    """Estimate UI scale from the chat menu icon match size."""
    if chat_menu_bbox is None:
        return 1.0
    try:
        base_w = int(chatMenuImg.shape[1])
        w = int(chat_menu_bbox[2])
        if base_w <= 0 or w <= 0:
            return 1.0
        s = float(w) / float(base_w)
        # Clamp to reasonable bounds to avoid wild geometry.
        if s < 0.3:
            return 0.3
        if s > 2.0:
            return 2.0
        return s
    except Exception:
        return 1.0


def _dump_chat_fail(
    screenshot: GrayImage,
    *,
    reason: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not get_bool({}, '_', env_var='FENRIL_DUMP_CHAT_ON_FAIL', default=False, prefer_env=True):
        return
    try:
        ts = int(time.time())
        out_dir = pathlib.Path('debug')
        out_dir.mkdir(parents=True, exist_ok=True)
        meta: Dict[str, Any] = {
            'ts': ts,
            'when': datetime.utcnow().isoformat() + 'Z',
            'reason': str(reason),
            'shape': getattr(screenshot, 'shape', None),
        }
        if isinstance(extra, dict):
            meta.update(extra)
        (out_dir / f'chat_fail_{ts}.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
        cv2.imwrite(str(out_dir / f'chat_fail_{ts}.png'), screenshot)
    except Exception:
        pass


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
        scale = _chat_scale_from_menu(chatMenuPosition)
        x_off = int(round(18 * scale))
        y = int(chatMenuPosition[1])
        height = max(1, int(round(20 * scale)))
        x = int(leftSidebarArrowsPosition[0] + x_off)
        width = int(chatMenuPosition[0] - x)
        if width <= 0 or height <= 0:
            return {}
        chatsTabsContainerImage = screenshot[y:y + height, x:x + width]
        if chatsTabsContainerImage.size == 0:
            return {}
        while shouldFindTabs:
            tab_step = max(1, int(round(96 * scale)))
            xOfTab = tabIndex * tab_step
            if xOfTab < 0 or xOfTab >= chatsTabsContainerImage.shape[1]:
                break
            firstPixel = chatsTabsContainerImage[0, xOfTab]
            # Older code relied on exact pixel values (114/125) which breaks under
            # capture scaling, UI themes, or minor gamma changes. Use a tolerance.
            if int(firstPixel) < 80 or int(firstPixel) > 170:
                shouldFindTabs = False
                continue
            y1 = max(0, int(round(2 * scale)))
            y2 = min(chatsTabsContainerImage.shape[0], int(round(16 * scale)))
            x1 = max(0, xOfTab + int(round(2 * scale)))
            x2 = min(chatsTabsContainerImage.shape[1], x1 + int(round(92 * scale)))
            tabImage = chatsTabsContainerImage[y1:y2, x1:x2]
            if tabImage.size == 0:
                break
            # Normalize to canonical size before hashing.
            try:
                tab_norm = cv2.resize(tabImage, (92, 14), interpolation=cv2.INTER_AREA)
            except Exception:
                tab_norm = tabImage
            tabName = hashes['tabs'].get(hashit(tab_norm), 'Unknown')
            if tabName != 'Unknown':
                tabs.setdefault(
                    tabName,
                    {
                        'isSelected': int(firstPixel) <= 120,
                        'position': (x + xOfTab, y, int(round(92 * scale)), int(round(14 * scale))),
                    },
                )
            tabIndex += 1
        if tabs:
            return tabs

    # Fallback: template-based tab detection (more robust than hashing/geometry
    # when OBS scaling/UI layout shifts break the left-arrow anchor).
    try:
        if chatMenuPosition is None:
            chatMenuPosition = getChatMenuPosition(screenshot)
        scale = _chat_scale_from_menu(chatMenuPosition)
        try:
            h, w = screenshot.shape[:2]
        except Exception:
            return {}

        y0 = int(h * 0.55)
        x0 = 0
        roi = screenshot[y0:h, x0:int(w * 0.90)]
        if roi.size == 0:
            return {}

        # Search around the estimated scale.
        base_scales = (0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15)
        scales = tuple(max(0.3, min(2.0, float(scale) * s)) for s in base_scales)

        # Order matters: if a tab is selected, we want that first.
        from .config import images as _tab_images

        tab_specs = [
            ('local chat', ['localChat']),
            ('loot', ['loot']),
            ('npcs', ['npcs']),
        ]
        for tab_name, keys in tab_specs:
            found = None
            found_variant = None
            for key in keys:
                # Use the config's loaded images directly (not hashes).
                for variant in ('selected', 'unselected', 'newestMessage', 'unreadMessage'):
                    templ = _tab_images['tabs'].get(key, {}).get(variant)
                    if templ is None:
                        continue
                    bbox = locateMultiScale(roi, templ, confidence=0.60, scales=scales)
                    if bbox is not None:
                        found = bbox
                        found_variant = variant
                        break
                if found is not None:
                    break

            if found is not None:
                fx, fy, fw, fh = found
                tabs.setdefault(
                    tab_name,
                    {
                        'isSelected': found_variant == 'selected',
                        'position': (x0 + fx, y0 + fy, fw, fh),
                    },
                )

        return tabs
    except Exception:
        return tabs


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
    # On first observation, initialize state but do not treat existing chat history as "new loot".
    # This avoids startup false-positives when the Loot tab already contains previous loot lines.
    if len(listOfLootCheck) != 0 and len(oldListOfLootCheck) == 0:
        oldListOfLootCheck = listOfLootCheck
        return False
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

    # Scale-normalize the message area so template matching is stable under OBS scaling.
    chat_menu = getChatMenuPosition(screenshot)
    scale = _chat_scale_from_menu(chat_menu)
    inv = 1.0 / scale if scale > 0 else 1.0
    if abs(scale - 1.0) >= 0.03:
        try:
            new_w = max(1, int(round(messages.shape[1] * inv)))
            new_h = max(1, int(round(messages.shape[0] * inv)))
            interp = cv2.INTER_AREA if inv < 1.0 else cv2.INTER_LINEAR
            messages_norm = cv2.resize(messages, (new_w, new_h), interpolation=interp)
        except Exception:
            messages_norm = messages
            scale = 1.0
    else:
        messages_norm = messages

    # NOTE: locateMultiple signature is (compare_image, template). The old code had args reversed.
    lootLines = locateMultiple(messages_norm, lootOfTextImg, confidence=0.82)
    linesWithLoot = []
    for line in lootLines:
        # Map normalized coords back to original screenshot coords.
        ly = int(round(line[1] * scale))
        lh = max(1, int(round(line[3] * scale)))
        line_bbox = (x, y + ly, w, lh)

        # Work in normalized space for the "nothing" template as well.
        lineImg_norm = messages_norm[line[1]:line[1] + line[3], 0:messages_norm.shape[1]]
        # NOTE: locate signature is (compare_image, template). The old code had args reversed.
        nothingFound = locate(lineImg_norm, nothingTextImg, confidence=0.82)
        if nothingFound is None:
            lineImg = screenshot[line_bbox[1]:line_bbox[1] + line_bbox[3], line_bbox[0]:line_bbox[0] + line_bbox[2]]
            linesWithLoot.append((lineImg, line_bbox))
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
    chatMenu = getChatMenuPosition(screenshot)
    chatStatus = getChatStatus(screenshot)
    chatStatusPos = chatStatus[0] if isinstance(chatStatus, tuple) else None

    if chatMenu is None or chatStatusPos is None:
        _dump_chat_fail(
            screenshot,
            reason='chat messages anchors missing',
            extra={
                'chatMenu': list(chatMenu) if isinstance(chatMenu, (list, tuple)) else None,
                'chatStatus': list(chatStatusPos) if isinstance(chatStatusPos, (list, tuple)) else None,
            },
        )
        return None

    scale = _chat_scale_from_menu(chatMenu)

    # Derive left boundary from detected tabs when available.
    try:
        tabs = getTabs(screenshot)
        tab_lefts = [int(v.get('position', (999999, 0, 0, 0))[0]) for v in tabs.values() if isinstance(v, dict)]
        x_left = min(tab_lefts) if tab_lefts else int(round(5 * scale))
    except Exception:
        x_left = int(round(5 * scale))

    x_left = max(0, int(x_left))
    y_top = int(chatMenu[1] + int(round(18 * scale)))
    x_right = int(chatStatusPos[0] + int(round(40 * scale)))
    width = int(x_right - x_left)
    height = int((chatStatusPos[1] - int(round(6 * scale))) - (chatMenu[1] + int(round(13 * scale))))

    if width <= 0 or height <= 0:
        _dump_chat_fail(
            screenshot,
            reason='chat messages bbox invalid',
            extra={
                'x_left': x_left,
                'y_top': y_top,
                'x_right': x_right,
                'width': width,
                'height': height,
                'scale': scale,
                'chatMenu': list(chatMenu),
                'chatStatus': list(chatStatusPos),
            },
        )
        return None
    return (x_left, y_top, width, height)
