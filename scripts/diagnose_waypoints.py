from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


def _select_enabled_profile(data: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    table = data.get('_default')
    if not isinstance(table, dict):
        raise SystemExit("file.json: missing '_default' table")

    enabled: list[tuple[str, dict[str, Any]]] = []
    for k, row in table.items():
        if isinstance(row, dict) and row.get('enabled') is True:
            enabled.append((str(k), row))

    if not enabled:
        raise SystemExit('No enabled profile found in file.json')
    if len(enabled) > 1:
        ids = ', '.join(k for k, _ in enabled)
        raise SystemExit(f'Multiple enabled profiles found ({ids}).')
    return enabled[0]


def _is_coord(v: Any) -> bool:
    return isinstance(v, (list, tuple)) and len(v) >= 3 and all(isinstance(n, int) for n in v[:3])


def main() -> int:
    data = json.loads(Path('file.json').read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise SystemExit('file.json root must be a JSON object')

    pid, row = _select_enabled_profile(data)
    cfg = row.get('config')
    if not isinstance(cfg, dict):
        cfg = {}

    ng_cave = cfg.get('ng_cave')
    if not isinstance(ng_cave, dict):
        ng_cave = {}

    waypoints = ng_cave.get('waypoints')
    if not isinstance(waypoints, dict):
        waypoints = {}

    items = waypoints.get('items')
    if not isinstance(items, list):
        items = []

    print(f'profile_id: {pid}')
    print(f'ng_cave.enabled: {ng_cave.get("enabled")!r}')
    print(f'ng_cave.runToCreatures: {ng_cave.get("runToCreatures")!r}')
    print(f'waypoints.count: {len(items)}')
    print(f'waypoints.currentIndex: {waypoints.get("currentIndex")!r}')
    print(f'waypoints.state: {waypoints.get("state")!r}')

    if not items:
        print('WARNING: no waypoints in profile (cavebot will never reach the cave).')
        return 2

    # Count waypoint types.
    types: list[str] = []
    for it in items:
        if isinstance(it, dict):
            types.append(str(it.get('type', '')))
        else:
            types.append('<non-dict>')
    counts = Counter(types)
    print('types.counts:', dict(counts))

    # Validate structure.
    missing_direction: list[int] = []
    bad_coord: list[int] = []
    unknown_type: list[int] = []

    known_types = {
        'walk',
        'rightClickUse',
        'useLadder',
        'useRope',
        'useShovel',
        'moveDown',
        'moveUp',
        'singleMove',
        'rightClickDirection',
        'depositItems',
        'refillChecker',
        'travel',
        'singleWalk',
        'useHole',
        'openDoor',
    }
    needs_dir = {'moveDown', 'moveUp', 'singleMove', 'rightClickDirection', 'singleWalk'}

    for i, it in enumerate(items):
        if not isinstance(it, dict):
            unknown_type.append(i)
            continue
        wtype = str(it.get('type', ''))
        coord = it.get('coordinate')
        if not _is_coord(coord):
            bad_coord.append(i)
        opts = it.get('options')
        if not isinstance(opts, dict):
            opts = {}
        if wtype in needs_dir and not isinstance(opts.get('direction'), str):
            missing_direction.append(i)
        if wtype and wtype not in known_types:
            unknown_type.append(i)

    if bad_coord:
        print('WARNING: waypoints with invalid coordinate indices:', bad_coord[:50])
    if missing_direction:
        print('WARNING: move/dir waypoints missing options.direction indices:', missing_direction[:50])
    if unknown_type:
        print('WARNING: waypoints with unknown type indices:', unknown_type[:50])

    # Helpful hint: currentIndex being non-None can keep the bot stuck on a stale index.
    cur = waypoints.get('currentIndex')
    if isinstance(cur, int) and (cur < 0 or cur >= len(items)):
        print('WARNING: currentIndex is out of range for items. Resetting to None is recommended.')
    if cur is not None:
        print('HINT: If you started the run from a different place, consider resetting currentIndex/state to None so the bot picks the closest waypoint.')

    # Print a small sample.
    print('first3:', items[:3])
    print('last3:', items[-3:])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
