from numba import njit
import numpy as np
from typing import Generator, Optional, Union
from src.shared.typings import CreatureCategory, CreatureCategoryOrUnknown, GrayImage
from src.utils.core import hashit, locate
from .config import creaturesNamesImagesHashes, images
from .extractors import getCreaturesNamesImages
from .typings import CreatureList, Creature


# PERF: [0.13737060000000056, 4.999999987376214e-07]
@njit(cache=True, fastmath=True)
def getBeingAttackedCreatureCategory(creatures: CreatureList) -> Union[CreatureCategory, None]:
    for creature in creatures:
        if creature['isBeingAttacked']:
            return creature['name']
    return None


# PERF: [1.3400000000274304e-05, 2.9000000001389026e-06]
@njit(cache=True, fastmath=True)
def getBeingAttackedCreatures(content: GrayImage, filledSlotsCount: int) -> Generator[bool, None, None]:
    alreadyCalculatedBeingAttackedCreature = False
    for creatureIndex in range(filledSlotsCount):
        contentIndex = creatureIndex * 22
        if alreadyCalculatedBeingAttackedCreature:
            yield False
        else:
            # Detect the target frame around the 20x20 creature icon.
            # In practice, the attack frame produces a nearly-uniform 1px border,
            # while the regular icon border varies. Selection highlight can create
            # a uniform *white* border, so explicitly filter that out.
            border_sum = 0
            border_count = 0
            border_min = 255
            border_max = 0

            # top + bottom rows
            y0 = contentIndex
            y1 = contentIndex + 19
            for x in range(20):
                v0 = int(content[y0, x])
                v1 = int(content[y1, x])
                border_sum += v0 + v1
                border_count += 2
                if v0 < border_min:
                    border_min = v0
                if v0 > border_max:
                    border_max = v0
                if v1 < border_min:
                    border_min = v1
                if v1 > border_max:
                    border_max = v1

            # left + right cols (excluding corners)
            for y in range(1, 19):
                v0 = int(content[contentIndex + y, 0])
                v1 = int(content[contentIndex + y, 19])
                border_sum += v0 + v1
                border_count += 2
                if v0 < border_min:
                    border_min = v0
                if v0 > border_max:
                    border_max = v0
                if v1 < border_min:
                    border_min = v1
                if v1 > border_max:
                    border_max = v1

            border_mean = border_sum / border_count
            border_range = border_max - border_min

            # NOTE: keep this conservative: avoid highlight-only borders (255)
            # and require a near-uniform border.
            isBeingAttacked = (border_range <= 2) and (border_mean < 240.0) and (border_mean > 40.0)
            yield isBeingAttacked
            if isBeingAttacked:
                alreadyCalculatedBeingAttackedCreature = True


# PERF: [0.00017040000000001498, 7.330000000038694e-05]
def getCreatures(content: Optional[GrayImage]) -> CreatureList:
    if content is not None:
        filledSlotsCount = getFilledSlotsCount(content)
        if filledSlotsCount == 0:
            return np.array([], dtype=Creature)
        beingAttackedCreatures = [
            beingAttackedCreature for beingAttackedCreature in getBeingAttackedCreatures(content, filledSlotsCount)]
        creaturesNames = [creatureName for creatureName in getCreaturesNames(
            content, filledSlotsCount)]
        creatures = np.array([(creatureName, beingAttackedCreatures[slotIndex])
                        for slotIndex, creatureName in enumerate(creaturesNames)], dtype=Creature)
        creaturesAfterCheck = checkDust(content, creatures)
        return creaturesAfterCheck
    else:
        return np.array([], dtype=Creature)


# PERF: [0.019119499999998624, 4.020000000082291e-05]
def getCreaturesNames(content: GrayImage, filledSlotsCount: int) -> Generator[CreatureCategoryOrUnknown, None, None]:
    for creatureNameImage in getCreaturesNamesImages(content, filledSlotsCount):
        yield creaturesNamesImagesHashes.get(hashit(creatureNameImage), 'Unknown')


# PERF: [0.5794668999999999, 3.9999999934536845e-07]
@njit(cache=True, fastmath=True)
def getFilledSlotsCount(content: GrayImage) -> int:
    filledSlotsCount = 0
    for slotIndex in range(len(content) // 22):
        y = 22 * slotIndex

        # Fast path: legacy exact-color detection (works for the original theme).
        v0 = content[:, 23][y + 11]
        v1 = content[:, 23][y + 10]
        v2 = content[:, 23][y + 4]
        v3 = content[:, 23][y + 5]
        # Use a small tolerance to handle compression/gamma drift in test fixtures.
        iv0 = int(v0)
        iv1 = int(v1)
        iv2 = int(v2)
        iv3 = int(v3)
        if (
            (190 <= iv0 <= 194) or (245 <= iv0 <= 249)
            or (190 <= iv1 <= 194) or (245 <= iv1 <= 249)
            or (190 <= iv2 <= 194) or (245 <= iv2 <= 249)
            or (190 <= iv3 <= 194) or (245 <= iv3 <= 249)
        ):
            filledSlotsCount += 1
            continue

        # Fallback: adaptive contrast detection on the name row.
        # Name row is at y+11 and spans columns 23:138 (115px).
        row_y = y + 11
        min_v = 255
        max_v = 0
        for x in range(23, 138):
            v = content[row_y, x]
            if v < min_v:
                min_v = v
            if v > max_v:
                max_v = v

        # If the row is nearly flat (or only slightly noisy), treat it as empty.
        # For dark themes, names are bright, so also require a few bright pixels.
        diff = int(max_v) - int(min_v)
        bright = 0
        for x in range(23, 138):
            if int(content[row_y, x]) >= 160:
                bright += 1

        if diff >= 20 and bright >= 2:
            filledSlotsCount += 1
        else:
            break
    return filledSlotsCount


# PERF: [7.5999999999964984e-06, 7.999999986907369e-07]
def hasSkull(content: GrayImage, creatures: CreatureList) -> bool:
    for creatureIndex, creature in enumerate(creatures):
        if creature['name'] != 'Unknown':
            continue
        y = (creatureIndex * 22)
        creatureIconsImage = content[y + 2:y + 13, -38:-2]
        if locate(creatureIconsImage, images['skulls']['black']):
            return True
        if locate(creatureIconsImage, images['skulls']['orange']):
            return True
        if locate(creatureIconsImage, images['skulls']['red']):
            return True
        if locate(creatureIconsImage, images['skulls']['white']):
            return True
        if locate(creatureIconsImage, images['skulls']['yellow']):
            return True
    return False

def checkDust(content: GrayImage, creatures: CreatureList) -> CreatureList:
    for creatureIndex, creature in enumerate(creatures):
        if creature['name'] != 'Unknown':
            continue
        y = (creatureIndex * 22)
        creatureIconsImage = content[y + 2:y + 13, -38:-2]
        if locate(creatureIconsImage, images['icons']['dust'], confidence=0.75):
            creature['name'] = 'Dusted'
    return creatures

# PERF: [4.499999999296733e-06, 9.999999992515995e-07]
@njit(cache=True, fastmath=True)
def isAttackingSomeCreature(creatures: CreatureList) -> bool:
    if creatures is not None and len(creatures) > 0:
        for isBeingAttacked in creatures['isBeingAttacked']:
            if isBeingAttacked:
                return True
    return False
