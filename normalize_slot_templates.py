"""Convenience entrypoint for scripts/normalize_slot_templates.py.

Allows running from repo root:
- `python normalize_slot_templates.py ...`

Equivalent to:
- `python scripts/normalize_slot_templates.py ...`
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    target = repo_root / 'scripts' / 'normalize_slot_templates.py'
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
