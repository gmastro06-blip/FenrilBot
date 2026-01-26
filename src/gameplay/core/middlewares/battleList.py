import numpy as np
import os
import pathlib
from datetime import datetime

import cv2

from src.repositories.battleList.core import getCreatures, isAttackingSomeCreature
from src.repositories.battleList.extractors import getContent, getCreaturesNamesImages
from src.repositories.battleList.locators import getBattleListIconPosition, getContainerBottomBarPosition
from src.repositories.battleList.typings import Creature
from src.utils.console_log import log_throttled
from src.utils.runtime_settings import get_bool, get_float, get_str
from ...typings import Context


_PREFERRED_NAME_TEMPLATES: dict[str, np.ndarray] = {}


def _canonicalize_name_row(row: np.ndarray) -> np.ndarray:
    # Mirror battleList.extractors.getCreaturesNamesImages canonicalization (1D row length 115).
    if row is None or row.size == 0:
        return np.zeros((115,), dtype=np.uint8)
    row = np.ascontiguousarray(row).astype(np.uint8)
    if row.shape[0] != 115:
        # Keep it safe: resize by simple crop/pad.
        out = np.zeros((115,), dtype=np.uint8)
        n = min(115, int(row.shape[0]))
        out[:n] = row[:n]
        row = out

    min_v = int(row.min())
    max_v = int(row.max())
    out = np.zeros((115,), dtype=np.uint8)
    if max_v < 120:
        thr = min_v + 10
        for i, v in enumerate(row):
            iv = int(v)
            if iv == 192 or iv == 247 or iv >= thr:
                out[i] = 192
    else:
        for i, v in enumerate(row):
            iv = int(v)
            if iv == 192 or iv == 247 or iv >= 170:
                out[i] = 192
    return out


def _canonicalize_name_band(band: np.ndarray) -> np.ndarray:
    """Canonicalize a small (H x 115) band into a single 1D mask.

    Using multiple rows makes matching far more robust across themes/gamma.
    """
    if band is None or band.size == 0:
        return np.zeros((115,), dtype=np.uint8)
    try:
        band = np.ascontiguousarray(band).astype(np.uint8)
        if band.ndim == 1:
            return _canonicalize_name_row(band)
        # OR (max) the canonicalized rows.
        out = np.zeros((115,), dtype=np.uint8)
        for r in range(band.shape[0]):
            out = np.maximum(out, _canonicalize_name_row(band[r]))
        return out
    except Exception:
        return np.zeros((115,), dtype=np.uint8)


def _template_for_creature_name(name: str) -> np.ndarray | None:
    key = (name or '').strip().lower()
    if not key:
        return None
    cached = _PREFERRED_NAME_TEMPLATES.get(key)
    if cached is not None:
        return cached

    try:
        from src.utils.image import loadFromRGBToGray
    except Exception:
        return None

    try:
        # Keep path construction consistent with battleList/config.py.
        monsters_dir = pathlib.Path(__file__).resolve().parents[3] / 'repositories' / 'battleList' / 'images' / 'monsters'
        fp = monsters_dir / f'{name}.png'
        if not fp.exists():
            return None
        templ = loadFromRGBToGray(str(fp))
        # Use a thicker band than the legacy hashing (more robust).
        band2d = templ[6:11, 0:115]
        canon = _canonicalize_name_band(band2d)
        _PREFERRED_NAME_TEMPLATES[key] = canon
        return canon
    except Exception:
        return None


def _best_fuzzy_match(row: np.ndarray, preferred_names: list[str]) -> str | None:
    if row is None or row.size == 0:
        return None
    row = _canonicalize_name_band(row)
    if int(np.count_nonzero(row)) < 3:
        return None

    best_name: str | None = None
    best_score = 0.0

    # Allow a tiny horizontal shift (capture scaling/gamma can move edges).
    for name in preferred_names:
        templ = _template_for_creature_name(name)
        if templ is None:
            continue
        if int(np.count_nonzero(templ)) < 3:
            continue

        # Try small shifts of the template against the row.
        for shift in (-3, -2, -1, 0, 1, 2, 3):
            if shift == 0:
                a = row
                b = templ
            elif shift > 0:
                a = row[shift:]
                b = templ[:-shift]
            else:
                s = -shift
                a = row[:-s]
                b = templ[s:]
            if a.size == 0 or b.size == 0:
                continue
            score = float(np.mean(a == b))
            if score > best_score:
                best_score = score
                best_name = name

    # Threshold tuned to be forgiving (hashing is exact, this is approximate).
    if best_name is not None and best_score >= 0.85:
        return best_name
    return None


# TODO: add unit tests
def setBattleListMiddleware(context: Context) -> Context:
    screenshot = context.get('ng_screenshot')
    content = getContent(screenshot) if screenshot is not None else None
    creatures = getCreatures(content) if content is not None else np.array([], dtype=Creature)

    # If names are coming back as "Unknown" (common on different Tibia themes/capture gamma),
    # try a fuzzy resolution for preferred targets so name-based targeting still works.
    try:
        if content is not None and creatures is not None and len(creatures) > 0:
            prefer_raw = get_str(
                context,
                'ng_runtime.battlelist_prefer_names',
                env_var='FENRIL_BATTLELIST_PREFER_NAMES',
                default='',
                prefer_env=True,
            )
            preferred = [p.strip() for p in prefer_raw.replace(';', ',').split(',') if p.strip()]
            if preferred and hasattr(creatures, '__getitem__'):
                unknown_idxs = [i for i, c in enumerate(creatures) if str(c['name']).strip().lower() == 'unknown']
                if unknown_idxs:
                    from src.repositories.battleList.core import getFilledSlotsCount
                    filled = int(getFilledSlotsCount(content))
                    if filled > 0:
                        # Use a multi-row band around the name baseline.
                        for i in unknown_idxs:
                            if i < 0 or i >= filled:
                                continue
                            y = 11 + (i * 22)
                            y0 = max(0, y - 2)
                            y1 = min(int(content.shape[0]), y + 3)
                            band = content[y0:y1, 23:138]
                            match = _best_fuzzy_match(band, preferred)
                            if match is not None:
                                creatures[i]['name'] = match
    except Exception:
        # Never let fuzzy matching break the main loop.
        pass

    # Persist the last non-empty parsed list. This helps troubleshooting and can
    # optionally smooth over brief parsing glitches.
    dbg = context.get('ng_debug')
    if not isinstance(dbg, dict):
        dbg = {}
        context['ng_debug'] = dbg

    now_s = float(datetime.now().timestamp())
    if len(creatures) > 0:
        dbg['battleList_last_nonempty_s'] = now_s
        dbg['battleList_last_nonempty_count'] = int(len(creatures))
        # Keep a copy in ng_battleList so other code can use it if needed.
        try:
            context['ng_battleList']['last_nonempty_creatures'] = creatures
        except Exception:
            pass
    else:
        # Optional grace window: if parsing briefly returns 0 but we very recently
        # had a non-empty battle list, keep the last non-empty snapshot.
        grace_s = get_float(
            context,
            'ng_runtime.battlelist_grace_s',
            env_var='FENRIL_BATTLELIST_GRACE_S',
            default=0.0,
        )
        last_s = dbg.get('battleList_last_nonempty_s')
        last_creatures = None
        try:
            last_creatures = context.get('ng_battleList', {}).get('last_nonempty_creatures')
        except Exception:
            last_creatures = None

        if (
            grace_s > 0
            and isinstance(last_s, (int, float))
            and (now_s - float(last_s)) <= float(grace_s)
            and last_creatures is not None
            and len(last_creatures) > 0
        ):
            creatures = last_creatures
            dbg['battleList_used_grace'] = True
        else:
            dbg['battleList_used_grace'] = False

    context['ng_battleList']['creatures'] = creatures

    if (
        get_bool(
            context,
            'ng_runtime.warn_on_battlelist_empty',
            env_var='FENRIL_WARN_ON_BATTLELIST_EMPTY',
            default=True,
        )
        and screenshot is not None
        and content is not None
        and len(context['ng_battleList']['creatures']) == 0
    ):
        icon_pos = getBattleListIconPosition(screenshot)
        raw_list = None
        bottom_pos = None
        try:
            if icon_pos is not None:
                raw_list = screenshot[
                    icon_pos[1] + icon_pos[3] + 1:,
                    icon_pos[0] - 1:icon_pos[0] - 1 + 156,
                ]
                bottom_pos = getContainerBottomBarPosition(raw_list)
        except Exception:
            raw_list = None
            bottom_pos = None

        log_throttled(
            'battleList.empty',
            'warn',
            'Battle list detected but has 0 entries. Check Tibia battle list filters (Players/NPCs/Monsters) and ensure the list is visible in the capture. '
            f"(diag: icon={icon_pos is not None} bottom={bottom_pos is not None} grace={dbg.get('battleList_used_grace')})",
            10.0,
        )

        # Optional: dump images to help debug why parsing is empty.
        if get_bool(
            context,
            'ng_runtime.dump_battlelist_on_empty',
            env_var='FENRIL_DUMP_BATTLELIST_ON_EMPTY',
            default=False,
        ):
            # Throttle dumps to avoid flooding the debug folder.
            last_dump_s = dbg.get('battleList_empty_last_dump_s')
            # Default interval is intentionally high to avoid flooding `debug/`.
            min_interval_s = get_float(
                context,
                'ng_runtime.dump_battlelist_min_interval_s',
                env_var='FENRIL_DUMP_BATTLELIST_MIN_INTERVAL_S',
                default=120.0,
            )
            if not isinstance(last_dump_s, (int, float)) or (now_s - float(last_dump_s)) >= min_interval_s:
                dbg['battleList_empty_last_dump_s'] = now_s
                try:
                    debug_dir = pathlib.Path('debug')
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

                    full_path = debug_dir / f'battlelist_empty_{ts}_full.png'
                    content_path = debug_dir / f'battlelist_empty_{ts}_content.png'

                    cv2.imwrite(str(full_path), np.ascontiguousarray(screenshot))
                    cv2.imwrite(str(content_path), np.ascontiguousarray(content))

                    # Also dump the raw list crop (icon->bottom), if we can reproduce it.
                    icon_pos = getBattleListIconPosition(screenshot)
                    if icon_pos is not None:
                        raw_list = screenshot[
                            icon_pos[1] + icon_pos[3] + 1:,
                            icon_pos[0] - 1:icon_pos[0] - 1 + 156,
                        ]
                        raw_path = debug_dir / f'battlelist_empty_{ts}_raw.png'
                        cv2.imwrite(str(raw_path), np.ascontiguousarray(raw_list))

                    # Tell the user exactly where to look.
                    log_throttled(
                        'battleList.empty.dump',
                        'info',
                        f"battleList empty dump: full={full_path} content={content_path}",
                        1.0,
                    )
                except Exception:
                    # Never let debug dumping break the bot loop.
                    pass

    # Extra diagnostics: when the bot never attacks, the root cause is often that
    # the capture does not include the battle list (or it can't be matched).
    if get_bool(context, 'ng_runtime.targeting_diag', env_var='FENRIL_TARGETING_DIAG', default=False):
        dbg = context.get('ng_debug')
        if not isinstance(dbg, dict):
            dbg = {}
            context['ng_debug'] = dbg

        icon_pos = getBattleListIconPosition(screenshot) if screenshot is not None else None
        dbg['battleList_icon_found'] = icon_pos is not None
        dbg['battleList_content_found'] = content is not None

        raw_list = None
        bottom_pos = None
        if screenshot is not None and icon_pos is not None:
            raw_list = screenshot[
                icon_pos[1] + icon_pos[3] + 1:,
                icon_pos[0] - 1:icon_pos[0] - 1 + 156,
            ]
            bottom_pos = getContainerBottomBarPosition(raw_list)

        dbg['battleList_bottomBar_found'] = bottom_pos is not None
        dbg['battleList_raw_shape'] = getattr(raw_list, 'shape', None)
        dbg['battleList_content_shape'] = getattr(content, 'shape', None)

        log_throttled(
            'battleList.diag',
            'info',
            f"battleList: icon={dbg['battleList_icon_found']} content={dbg['battleList_content_found']} bottom={dbg['battleList_bottomBar_found']}",
            2.0,
        )

    context['ng_cave']['isAttackingSomeCreature'] = isAttackingSomeCreature(
        context['ng_battleList']['creatures'])
    return context
