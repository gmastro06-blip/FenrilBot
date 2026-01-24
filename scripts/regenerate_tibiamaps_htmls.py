from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _iter_waypoints_files(root: Path) -> list[Path]:
    """Return one pilotscript per folder.

    Preference order per directory:
    1) waypoints_edited.pilotscript
    2) waypoints.pilotscript
    3) any waypoints*.pilotscript
    """

    candidates = sorted(root.glob('**/waypoints*.pilotscript'))
    if not candidates:
        return []

    by_dir: dict[Path, list[Path]] = {}
    for path in candidates:
        by_dir.setdefault(path.parent, []).append(path)

    chosen: list[Path] = []
    for directory, paths in sorted(by_dir.items()):
        preferred = None
        for name in ('waypoints_edited.pilotscript', 'waypoints.pilotscript'):
            hit = directory / name
            if hit in paths:
                preferred = hit
                break
        chosen.append(preferred or sorted(paths)[0])

    return chosen


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description='Regenerate TibiaMaps Plotly HTML overlays for pilotscripts.')
    parser.add_argument(
        '--root',
        default='scripts-converted',
        help='Root folder to scan (default: scripts-converted)',
    )
    parser.add_argument(
        '--cache-dir',
        default='.cache/tibiamaps',
        help='TibiaMaps cache directory (default: .cache/tibiamaps)',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Limit number of scripts processed (0 = no limit)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would run, without executing',
    )
    args = parser.parse_args(argv)

    workspace_root = Path(__file__).resolve().parents[1]
    view_script = workspace_root / 'viewScript.py'
    if not view_script.exists():
        raise SystemExit(f'viewScript.py not found at {view_script}')

    scan_root = (workspace_root / args.root).resolve()
    if not scan_root.exists():
        raise SystemExit(f'Root not found: {scan_root}')

    scripts = _iter_waypoints_files(scan_root)
    if args.limit and args.limit > 0:
        scripts = scripts[: args.limit]

    if not scripts:
        print(f'No waypoints pilotscripts found under {scan_root}')
        return 0

    print(f'Found {len(scripts)} scripts under {scan_root}')

    for i, script_path in enumerate(scripts, start=1):
        out_dir = script_path.parent
        cmd = [
            sys.executable,
            str(view_script),
            str(script_path),
            '--tibiamaps-floors',
            'auto',
            '--tibiamaps-cache-dir',
            str(args.cache_dir),
            '--out',
            str(out_dir),
            '--no-open',
        ]

        rel = script_path.relative_to(workspace_root)
        print(f'[{i}/{len(scripts)}] {rel}')
        if args.dry_run:
            print('  ' + ' '.join(cmd))
            continue

        subprocess.run(cmd, check=True)

    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
