import cv2
import dxcam
import numpy as np
import hashlib
from typing import Callable, List, Optional, Union
from src.shared.typings import BBox, GrayImage


try:
    from farmhash import FarmHash64

    def _hash_bytes(data: bytes) -> int:
        return FarmHash64(data)
except Exception:

    def _hash_bytes(data: bytes) -> int:
        return int.from_bytes(
            hashlib.blake2b(data, digest_size=8).digest(),
            "little",
            signed=False,
        )


camera = dxcam.create(device_idx=0, output_idx=1, output_color='BGRA')
latestScreenshot = None


# TODO: add unit tests
def cacheObjectPosition(func: Callable[[GrayImage], Optional[BBox]]) -> Callable[[GrayImage], Optional[BBox]]:
    lastX = None
    lastY = None
    lastW = None
    lastH = None
    lastImgHash = None

    def inner(screenshot: GrayImage) -> Optional[BBox]:
        nonlocal lastX, lastY, lastW, lastH, lastImgHash
        if lastX != None and lastY != None and lastW != None and lastH != None:
            if hashit(screenshot[lastY:lastY + lastH, lastX:lastX + lastW]) == lastImgHash:
                return (lastX, lastY, lastW, lastH)
        res = func(screenshot)
        if res is None:
            return None
        lastX = res[0]
        lastY = res[1]
        lastW = res[2]
        lastH = res[3]
        lastImgHash = hashit(
            screenshot[lastY:lastY + lastH, lastX:lastX + lastW])
        return res
    return inner


# TODO: add unit tests
def hashit(arr: np.ndarray) -> int:
    data = np.ascontiguousarray(arr).tobytes()
    return _hash_bytes(data)


# TODO: add unit tests
def locate(compareImage: GrayImage, img: GrayImage, confidence: float = 0.85, type: int = cv2.TM_CCOEFF_NORMED) -> Optional[BBox]:
    match = cv2.matchTemplate(compareImage, img, type)
    res = cv2.minMaxLoc(match)
    if res[1] <= confidence:
        return None
    return res[3][0], res[3][1], len(img[0]), len(img)


# TODO: add unit tests
def locateMultiple(compareImg: GrayImage, img: GrayImage, confidence: float = 0.85) -> List[BBox]:
    match = cv2.matchTemplate(compareImg, img, cv2.TM_CCOEFF_NORMED)
    loc = np.where(match >= confidence)
    resultList = []
    for pt in zip(*loc[::-1]):
        resultList.append((pt[0], pt[1], len(compareImg[0]), len(compareImg)))
    return resultList


# TODO: add unit tests
def getScreenshot() -> Optional[GrayImage]:
    global camera, latestScreenshot
    screenshot = camera.grab()
    if screenshot is None:
        return latestScreenshot
    latestScreenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
    return latestScreenshot
