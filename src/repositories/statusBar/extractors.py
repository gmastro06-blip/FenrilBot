from src.shared.typings import BBox, GrayImage
from .config import barSize
import numpy as np


# TODO: add unit tests
# TODO: add perf
def getHpBar(screenshot: GrayImage, heartPos: BBox) -> GrayImage:
    # ERROR 7 FIXED: Validar dimensiones antes de extraer
    try:
        y0 = heartPos[1] + 5
        y1 = y0 + 1
        x0 = heartPos[0] + 13
        x1 = x0 + barSize
        
        # Verificar que no excedemos los límites del screenshot
        if y1 > screenshot.shape[0] or x1 > screenshot.shape[1]:
            return np.array([])
        
        bar = screenshot[y0:y1, x0:x1]
        if len(bar) == 0 or len(bar[0]) == 0:
            return np.array([])
        return bar[0]
    except (IndexError, KeyError) as e:
        return np.array([])


# TODO: add unit tests
# TODO: add perf
def getManaBar(screenshot: GrayImage, heartPos: BBox) -> GrayImage:
    # ERROR 7 FIXED: Validar dimensiones antes de extraer
    try:
        y0 = heartPos[1] + 5
        y1 = y0 + 1
        x0 = heartPos[0] + 14
        x1 = x0 + barSize
        
        # Verificar que no excedemos los límites del screenshot
        if y1 > screenshot.shape[0] or x1 > screenshot.shape[1]:
            return np.array([])
        
        bar = screenshot[y0:y1, x0:x1]
        if len(bar) == 0 or len(bar[0]) == 0:
            return np.array([])
        return bar[0]
    except (IndexError, KeyError) as e:
        return np.array([])
