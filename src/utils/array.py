from typing import List, TypeVar

T = TypeVar('T')

def getNextArrayIndex(items: List[T], currentIndex: int) -> int:
    return currentIndex + 1 if currentIndex < len(items) - 1 else 0
