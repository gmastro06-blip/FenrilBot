import argparse
import json
from pathlib import Path
from typing import Any


def _parse_value(raw: str, *, force_json: bool) -> Any:
    if force_json:
        return json.loads(raw)

    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"none", "null"}:
        return None

    # Try numbers (int first, then float)
    try:
        # Avoid treating hex-like strings or leading zeros as special;
        # int() handles signs and whitespace fine.
        if lowered.startswith("0") and lowered not in {"0", "0.0"} and raw.strip().isdigit():
            # Keep as string to avoid surprises (e.g., hotkeys like "01").
            raise ValueError
        return int(raw)
    except Exception:
        pass

    try:
        return float(raw)
    except Exception:
        pass

    # Finally: allow JSON literals/objects/arrays if the user pasted them.
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _select_profile(data: dict[str, Any], profile_id: str | None) -> tuple[str, dict[str, Any]]:
    table = data.get("_default")
    if not isinstance(table, dict):
        raise SystemExit("file.json: missing '_default' table")

    if profile_id is not None:
        row = table.get(profile_id)
        if not isinstance(row, dict):
            raise SystemExit(f"Profile id {profile_id!r} not found in file.json")
        return profile_id, row

    enabled: list[tuple[str, dict[str, Any]]] = []
    for k, row in table.items():
        if isinstance(row, dict) and row.get("enabled") is True:
            enabled.append((str(k), row))

    if len(enabled) == 0:
        raise SystemExit("No enabled profile found in file.json")
    if len(enabled) > 1:
        ids = ", ".join(k for k, _ in enabled)
        raise SystemExit(f"Multiple enabled profiles found ({ids}). Pass --profile-id to disambiguate.")
    return enabled[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set or get ng_runtime keys for the enabled profile in file.json",
    )
    parser.add_argument("--file", default="file.json", help="Path to file.json")
    parser.add_argument("--profile-id", default=None, help="Explicit profile id inside _default")

    parser.add_argument("--key", required=True, help="ng_runtime key to set/get")
    parser.add_argument(
        "--get",
        action="store_true",
        help="Print current value (does not modify file.json)",
    )
    parser.add_argument(
        "--value",
        default=None,
        help="Value to set (auto-parses true/false/null/numbers/json; otherwise string)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Force parsing --value as JSON",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")

    args = parser.parse_args()

    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("file.json root must be a JSON object")

    pid, row = _select_profile(data, args.profile_id)

    cfg = row.get("config")
    if not isinstance(cfg, dict):
        cfg = {}
        row["config"] = cfg

    ng = cfg.get("ng_runtime")
    if not isinstance(ng, dict):
        ng = {}
        cfg["ng_runtime"] = ng

    key = str(args.key)
    if args.get:
        print(f"profile_id {pid}")
        print(f"ng_runtime.{key} {ng.get(key)!r}")
        return 0

    if args.value is None:
        raise SystemExit("--value is required unless --get is used")

    new_value = _parse_value(str(args.value), force_json=bool(args.json))
    old_value = ng.get(key, "<missing>")

    changed = old_value != new_value
    print(f"profile_id {pid}")
    print(f"ng_runtime.{key}: {old_value!r} -> {new_value!r}")
    print(f"changed {changed}")

    if changed and not args.dry_run:
        ng[key] = new_value
        path.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print("written", str(path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
