from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

# Ensure project root is on sys.path so `import src.*` works when running from `scripts/`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.radar.core import getCoordinate, getFloorLevel
from src.repositories.radar.extractors import getRadarImage
from src.repositories.radar.locators import getRadarToolsPosition


def _phase_shift(prev_img: np.ndarray, curr_img: np.ndarray):
    h = min(prev_img.shape[0], curr_img.shape[0])
    w = min(prev_img.shape[1], curr_img.shape[1])
    a = prev_img[:h, :w].astype(np.float32)
    b = curr_img[:h, :w].astype(np.float32)

    # High-pass-ish: subtract a blur to reduce lighting/UI banding effects.
    a = a - cv2.GaussianBlur(a, (0, 0), 2.0)
    b = b - cv2.GaussianBlur(b, (0, 0), 2.0)

    win = cv2.createHanningWindow((w, h), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(a, b, win)
    return float(dx), float(dy), float(resp), (h, w)


def main() -> int:
    # 1) Try analyzing full screenshots (may fail if tools template doesn't match those dumps).
    paths = sorted(Path('debug').glob('debug_dual_capture_*_gray_*.png'))
    print('debug_dual_capture count', len(paths))
    pairs: list[tuple[str, np.ndarray | None]] = []

    any_tools = False
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(p.name, 'img=None')
            pairs.append((p.name, None))
            continue

        tools = getRadarToolsPosition(img)
        any_tools = any_tools or (tools is not None)
        floor = getFloorLevel(img)
        radar = getRadarImage(img, tools) if tools is not None else None
        dbg: dict = {}
        coord = getCoordinate(img, previousCoordinate=None, debug=dbg)

        print(
            p.name,
            'img', img.shape,
            'tools', tools,
            'floor', floor,
            'radar', None if radar is None else radar.shape,
            'coord', coord,
            'dbg', {k: dbg.get(k) for k in ('radar_tools', 'floor_level') if k in dbg},
        )
        pairs.append((p.name, radar))

    if any_tools:
        for i in range(1, len(pairs)):
            n0, r0 = pairs[i - 1]
            n1, r1 = pairs[i]
            if r0 is None or r1 is None:
                continue
            dx, dy, resp, wh = _phase_shift(r0, r1)
            print('phase', n0, '->', n1, 'shift(dx,dy)=', (dx, dy), 'resp=', resp, 'wh=', wh)
    else:
        print('No radar tools detected in debug_dual_capture dumps; skipping screenshot-based phase shifts.')

    # 2) Analyze extracted radar crops from runtime diagnostics.
    crops = sorted(Path('debug').glob('dual_diag_radar_match_not_found_*_radar.png'))
    print('dual_diag radar crops count', len(crops))
    crop_pairs: list[tuple[str, np.ndarray]] = []
    for p in crops[-30:]:
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        crop_pairs.append((p.name, img))
    for i in range(1, len(crop_pairs)):
        n0, r0 = crop_pairs[i - 1]
        n1, r1 = crop_pairs[i]
        dx, dy, resp, wh = _phase_shift(r0, r1)
        print('crop phase', n0, '->', n1, 'shift(dx,dy)=', (dx, dy), 'resp=', resp, 'wh=', wh)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
