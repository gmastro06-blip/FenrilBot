from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.repositories.radar.config import floorsImgs


def _prep_raw(img: np.ndarray) -> np.ndarray:
    """Return image unchanged for raw template matching."""
    return img


def _prep_eq(img: np.ndarray) -> np.ndarray:
    return cv2.equalizeHist(img)


def _prep_edges(img: np.ndarray) -> np.ndarray:
    # Light blur then Canny; output is uint8.
    blur = cv2.GaussianBlur(img, (0, 0), 1.0)
    return cv2.Canny(blur, 40, 120)


def _best_match(floor: np.ndarray, tpl: np.ndarray) -> tuple[float, tuple[int, int]]:
    # TM_CCOEFF_NORMED in [ -1, 1 ]
    res = cv2.matchTemplate(floor, tpl, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
    return float(max_val), (int(max_loc[0]), int(max_loc[1]))


def main() -> int:
    cand: list[Path] = []
    cand.extend(Path('debug').glob('dual_diag_radar_match_not_found_*.json'))
    cand.extend(Path('debug').glob('preflight_radar_match_not_found_*.json'))
    def _ts(p: Path) -> int:
        # filenames end with _<unix>.json
        try:
            return int(p.stem.split('_')[-1])
        except Exception:
            return 0

    jsons = sorted(cand, key=_ts)
    if not jsons:
        print('No radar debug json found (dual_diag/preflight)')
        return 1

    jpath = jsons[-1]
    meta = json.loads(jpath.read_text(encoding='utf-8'))
    fl = meta.get('floor_level')
    if fl is None:
        print('floor_level missing in', jpath.name)
        return 1
    floor_level = int(fl)
    radar_path = jpath.with_name(jpath.name.replace('.json', '_radar.png'))

    radar = cv2.imread(str(radar_path), cv2.IMREAD_GRAYSCALE)
    if radar is None:
        print('Failed to read radar crop', radar_path)
        return 1

    floor = floorsImgs[floor_level]

    print('using', jpath.name)
    print('floor_level', floor_level)
    print('floor', floor.shape, 'radar', radar.shape)

    preps = {
        'raw': _prep_raw,
        'eq': _prep_eq,
        'edges': _prep_edges,
    }

    # Scales around what we've seen historically.
    scales = [0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1]

    for name, fn in preps.items():
        best: tuple[float, float | None, tuple[int, int] | None] = (-999.0, None, None)  # score, scale, loc
        for s in scales:
            tw = max(8, int(round(radar.shape[1] * s)))
            th = max(8, int(round(radar.shape[0] * s)))
            tpl = cv2.resize(radar, (tw, th), interpolation=cv2.INTER_AREA if s < 1.0 else cv2.INTER_LINEAR)
            score, loc = _best_match(fn(floor), fn(tpl))
            if score > best[0]:
                best = (score, s, loc)
        print(f'prep={name:5s} best_score={best[0]:.4f} scale={best[1]} loc={best[2]}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
