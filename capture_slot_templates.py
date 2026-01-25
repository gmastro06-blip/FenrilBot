"""Convenience entrypoint for scripts/capture_slot_templates.py.

Some terminals/users run `python capture_slot_templates.py` from repo root.
Keep this wrapper so both of these work:
- `python scripts/capture_slot_templates.py ...`
- `python capture_slot_templates.py ...`
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    target = repo_root / 'scripts' / 'capture_slot_templates.py'
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
