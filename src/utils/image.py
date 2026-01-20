import cv2
from numba import njit
import numpy as np
from PIL import Image
from typing import Any, Callable, Optional, Sequence, Union, cast
from src.shared.typings import BBox, GrayImage
from src.utils.core import hashit, locate


# TODO: add types
# TODO: add unit tests
def cacheChain(imageList: Sequence[GrayImage]) -> Callable[[Callable[..., Any]], Callable[[GrayImage], Union[BBox, None]]]:
    def decorator(_: Callable[..., Any]) -> Callable[[GrayImage], Union[BBox, None]]:
        lastX: Optional[int] = None
        lastY: Optional[int] = None
        lastW: Optional[int] = None
        lastH: Optional[int] = None
        lastImageHash: Optional[int] = None

        def inner(screenshot: GrayImage) -> Union[BBox, None]:
            nonlocal lastX, lastY, lastW, lastH, lastImageHash
            screenshot_arr = cast(Any, screenshot)
            if lastX is not None and lastY is not None and lastW is not None and lastH is not None and lastImageHash is not None:
                x = cast(int, lastX)
                y = cast(int, lastY)
                w = cast(int, lastW)
                h = cast(int, lastH)
                copiedImage = screenshot_arr[y:y + h, x:x + w]
                copiedImageHash = hashit(copiedImage)
                if copiedImageHash == lastImageHash:
                    return (x, y, w, h)
            for image in imageList:
                imagePosition = locate(screenshot, image)
                if imagePosition is not None:
                    (x, y, w, h) = imagePosition
                    lastX = x
                    lastY = y
                    lastW = w
                    lastH = h
                    lastImage = screenshot_arr[y:y + h, x:x + w]
                    lastImageHash = hashit(lastImage)
                    return (x, y, w, h)
            return None
        return inner
    return decorator


# TODO: add unit tests
@njit(cache=True, fastmath=True)
def convertGraysToBlack(arr: np.ndarray) -> np.ndarray:
    for i in range(len(arr)):
        for j in range(len(arr[0])):
            if arr[i, j] >= 50 and arr[i, j] <= 100:
                arr[i, j] = 0
    return arr


# TODO: add unit tests
def RGBtoGray(image: np.ndarray) -> GrayImage:
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


# TODO: add unit tests
def loadFromRGBToGray(path: str) -> GrayImage:
    return np.array(RGBtoGray(load(path)), dtype=np.uint8)


# TODO: add unit tests
def save(arr: GrayImage, name: str) -> None:
    im = Image.fromarray(arr)
    im.save(name)


# TODO: add unit tests
def crop(image: GrayImage, x: int, y: int, width: int, height: int) -> GrayImage:
    return image[y:y + height, x:x + width]


# TODO: add unit tests
def load(path: str) -> np.ndarray:
    bgr = cv2.imread(path)
    if bgr is None:
        raise FileNotFoundError(path)
    return np.array(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)
