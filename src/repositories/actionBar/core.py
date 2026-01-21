import pytesseract
import math
import numpy as np
from typing import Union
import src.repositories.actionBar.extractors as actionBarExtractors
import src.repositories.actionBar.locators as actionBarLocators
from src.shared.typings import GrayImage
import src.utils.core as coreUtils
from .config import ActionBarHashes, ActionBarImages, hashes as _hashes, images as _images


hashes: ActionBarHashes = _hashes
images: ActionBarImages = _images


def _rescale_intensity_u8(
    image: np.ndarray,
    in_range: tuple[int, int] = (50, 175),
    out_range: tuple[int, int] = (0, 255),
) -> np.ndarray:
    image_u8 = image.astype(np.uint8, copy=False)
    in_min, in_max = in_range
    out_min, out_max = out_range

    if in_max <= in_min:
        return image_u8.copy()

    scaled = (image_u8.astype(np.float32) - float(in_min)) * (float(out_max - out_min) / float(in_max - in_min)) + float(out_min)
    return np.clip(scaled, out_min, out_max).astype(np.uint8)


def _equalize_hist_u8(image: np.ndarray) -> np.ndarray:
    image_u8 = image.astype(np.uint8, copy=False)
    hist = np.bincount(image_u8.ravel(), minlength=256)
    cdf = hist.cumsum()
    nonzero = cdf[cdf > 0]
    if nonzero.size == 0:
        return image_u8.copy()
    cdf_min = int(nonzero[0])
    cdf_max = int(nonzero[-1])
    if cdf_max == cdf_min:
        return image_u8.copy()

    lut = np.floor((cdf - cdf_min) * 255.0 / float(cdf_max - cdf_min)).clip(0, 255).astype(np.uint8)
    return lut[image_u8]

pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# TODO: add unit tests
# PERF: [0.04209370000000012, 9.999999999621423e-06]
def getSlotCount(screenshot: GrayImage, slot: int) -> Union[int, None]:
    leftSideArrowsPos = actionBarLocators.getLeftArrowsPosition(screenshot)
    if leftSideArrowsPos is None:
        return None
    x0 = leftSideArrowsPos[0] + leftSideArrowsPos[2] + \
        (slot * 2) + ((slot - 1) * 34)
    slotImage = screenshot[leftSideArrowsPos[1]:leftSideArrowsPos[1] + 34, x0:x0 + 34]
    digits = slotImage[24:32, 3:33]
    
    number_region_image = np.array(digits, dtype=np.uint8)

    stretch = _rescale_intensity_u8(number_region_image, in_range=(50, 175), out_range=(0, 255))
    equalized_image = _equalize_hist_u8(stretch)

    count = pytesseract.image_to_string(equalized_image, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

    if not count:
        return 0

    return int(count)

def getSlotCountOld(screenshot: GrayImage, slot: int) -> Union[int, None]:
    leftSideArrowsPos = actionBarLocators.getLeftArrowsPosition(screenshot)
    if leftSideArrowsPos is None:
        return None
    x0 = leftSideArrowsPos[0] + leftSideArrowsPos[2] + \
        (slot * 2) + ((slot - 1) * 34)
    slotImage = screenshot[leftSideArrowsPos[1]:leftSideArrowsPos[1] + 34, x0:x0 + 34]
    digits = slotImage[24:32, 2:32]
    count = 0
    for i in range(5):
        x = ((6 * (5 - i)) - 3)
        number = images['digits'].get(
            coreUtils.hashit(digits[2:6, x:x + 1]), None)
        if number is None:
            number = 0
            continue
        count += number * (10 ** i)
    return count

# PERF: [0.08509680000000008, 0.00037780000000031677]
def hasCooldownByImage(screenshot: GrayImage, cooldownImage: GrayImage) -> Union[bool, None]:
    listOfCooldownsImage = actionBarExtractors.getCooldownsImage(screenshot)
    if listOfCooldownsImage is None:
        return None
    cooldownImagePosition = coreUtils.locate(
        listOfCooldownsImage, cooldownImage)
    if cooldownImagePosition is None:
        return False
    x = int(cooldownImagePosition[0])
    w = int(cooldownImagePosition[2])
    return listOfCooldownsImage[20:21, x:x + w][0][0] == 255


# TODO: add unit tests
# PERF: [0.08509680000000008, 0.00037780000000031677]
def hasCooldownByName(screenshot: GrayImage, name: str) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns'][name])


# PERF: [2.1100000000107144e-05, 5.5999999997169425e-06]
def hasAttackCooldown(screenshot: GrayImage) -> Union[bool, None]:
    listOfCooldownsImage = actionBarExtractors.getCooldownsImage(screenshot)
    if listOfCooldownsImage is None:
        return None
    cooldownImageHash = coreUtils.hashit(listOfCooldownsImage[0:20, 4:24])
    hashName = hashes['cooldowns'].get(cooldownImageHash, 'unknown')
    return hashName == 'attack'


# TODO: improve performance
# PERF: [0.08131169999999965, 0.00037539999999980367]
def hasExoriCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['exori'])


# TODO: improve performance
# PERF: [0.08513510000000002, 0.00037559999999992044]
def hasExoriGranCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['exori gran'])


# TODO: improve performance
# PERF: [0.08332179999999978, 0.000373600000000085]
def hasExoriMasCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['exori mas'])


# TODO: improve performance
# TODO: add unit tests
# PERF: [0.08801449999999988, 0.000378400000000223]
def hasExuraGranIcoCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['utura gran'])


# TODO: improve performance
# PERF: [0.08647640000000001,  0.0003741999999999912]
def hasExoriMinCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['exori min'])


# PERF: [2.7100000000057634e-05, 5.4999999998806e-06]
def hasHealingCooldown(screenshot: GrayImage) -> Union[bool, None]:
    listOfCooldownsImage = actionBarExtractors.getCooldownsImage(screenshot)
    if listOfCooldownsImage is None:
        return None
    cooldownImageHash = coreUtils.hashit(listOfCooldownsImage[0:20, 29:49])
    hashName = hashes['cooldowns'].get(cooldownImageHash, 'unknown')
    return hashName == 'healing'


# PERF: [2.0099999999523277e-05, 5.50000000032469e-06]
def hasSupportCooldown(screenshot: GrayImage) -> Union[bool, None]:
    listOfCooldownsImage = actionBarExtractors.getCooldownsImage(screenshot)
    if listOfCooldownsImage is None:
        return None
    cooldownImageHash = coreUtils.hashit(listOfCooldownsImage[0:20, 54:74])
    hashName = hashes['cooldowns'].get(cooldownImageHash, 'unknown')
    return hashName == 'support'


# TODO: improve performance
# TODO: add unit tests
# PERF: [0.08165200000000006, 0.0003780999999998258]
def hasUturaCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['utura'])


# TODO: improve performance
# TODO: add unit tests
# PERF: [0.0844541999999997, 0.0003747000000000611]
def hasUturaGranCooldown(screenshot: GrayImage) -> Union[bool, None]:
    return hasCooldownByImage(screenshot, images['cooldowns']['utura gran'])


# PERF: [0.03996639999999996, 4.199999999787707e-06]
def slotIsEquipped(screenshot: GrayImage, slot: int) -> Union[bool, None]:
    leftSideArrowsPos = actionBarLocators.getLeftArrowsPosition(screenshot)
    if leftSideArrowsPos is None:
        return None
    x0 = leftSideArrowsPos[0] + leftSideArrowsPos[2] + \
        (slot * 2) + ((slot - 1) * 34)
    slotImage = screenshot[leftSideArrowsPos[1]
        :leftSideArrowsPos[1] + 34, x0:x0 + 34]
    return slotImage[0, 0] == 41


# PERF: [0.04092479999999998, 4.300000000068138e-06]
def slotIsAvailable(screenshot: GrayImage, slot: int) -> Union[bool, None]:
    leftSideArrowsPos = actionBarLocators.getLeftArrowsPosition(screenshot)
    if leftSideArrowsPos is None:
        return None
    x0 = leftSideArrowsPos[0] + leftSideArrowsPos[2] + \
        (slot * 2) + ((slot - 1) * 34)
    slotImage = screenshot[leftSideArrowsPos[1]
        :leftSideArrowsPos[1] + 34, x0:x0 + 34]
    return not (slotImage[1, 2] == 54 and slotImage[1, 4] == 54 and slotImage[1, 6] == 54 and slotImage[1, 8] == 54 and slotImage[1, 10] == 54)
