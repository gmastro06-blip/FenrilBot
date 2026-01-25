"""Batch-upgrade legacy action markers inside scripts-converted.

Why:
- Many converted pilotscripts still contain legacy `walk + options.action` markers
  (e.g. `buy_potions`) that the current cavebot resolver ignores.
- This script upgrades those markers into real waypoint types that the bot runs.

Current scope:
- Converts `options.action == "buy_potions"` waypoints into `type: "refill"`.
- Derives potion item + target quantity from matching `scripts-master/**/setup_*.json`.

Safe-by-default:
- Supports `--dry-run`.
- Creates a `.bak` backup before overwriting (can be disabled).

Usage examples:
  python scripts/batch_upgrade_legacy_actions.py --dry-run
  python scripts/batch_upgrade_legacy_actions.py --setup auto
  python scripts/batch_upgrade_legacy_actions.py --setup mage
  python scripts/batch_upgrade_legacy_actions.py --setup setup_ek.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CONVERTED = ROOT / "scripts-converted"
SCRIPTS_MASTER = ROOT / "scripts-master"


DEFAULT_SETUP_PRIORITY = [
    # Most commonly used in this repo
    "mage",
    "ms",
    "ek",
    "rp",
    # Variants
    "ek_nonpvp",
    "ek_nopvp",
]


MANA_POTION_CANONICAL = {
    'mana potion': 'Mana Potion',
    'strong mana potion': 'Strong Mana Potion',
    'great mana potion': 'Great Mana Potion',
    'ultimate mana potion': 'Ultimate Mana Potion',
}

HEALTH_POTION_CANONICAL = {
    'small health potion': 'Small Health Potion',
    'health potion': 'Health Potion',
    'strong health potion': 'Strong Health Potion',
    'great health potion': 'Great Health Potion',
    'ultimate health potion': 'Ultimate Health Potion',
    'supreme health potion': 'Supreme Health Potion',
}


@dataclass(frozen=True)
class FileResult:
    path: str
    modified: bool
    converted_buy_potions: int
    converted_check_supplies: int
    converted_sell: int
    skipped_buy_potions: int
    skipped_check_supplies: int
    skipped_sell: int
    setup_used: Optional[str]
    reason: Optional[str] = None


def _safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            value = value.strip()
            return int(value) if value else 0
        return int(value)
    except Exception:
        return 0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


def _find_setup_files_for_rel_dir(rel_dir: Path) -> List[Path]:
    # Some converted folders are nested (e.g. "killer_caimans/killer_caimans").
    # Walk upwards until we find a matching scripts-master folder.
    current = rel_dir
    while True:
        setup_dir = SCRIPTS_MASTER / current
        if setup_dir.exists() and setup_dir.is_dir():
            files = sorted(setup_dir.glob("setup_*.json"))
            if files:
                return files
        if current == Path('.'):
            break
        current = current.parent
    return []


def _get_existing_refill_options(waypoints: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for wp in waypoints:
        if not isinstance(wp, dict):
            continue
        if wp.get('type') != 'refill':
            continue
        opts = wp.get('options')
        if not isinstance(opts, dict):
            continue
        # Ensure required keys exist so RefillTask won't crash.
        mana = opts.get('manaPotion')
        health = opts.get('healthPotion')
        if not (isinstance(mana, dict) and isinstance(health, dict)):
            continue
        if 'item' not in mana or 'quantity' not in mana:
            continue
        if 'item' not in health or 'quantity' not in health:
            continue
        if 'healthPotionEnabled' not in opts or 'houseNpcEnabled' not in opts:
            continue
        return opts
    return None


def _pick_setup_file(setup_files: List[Path], setup_selector: str) -> Optional[Path]:
    if not setup_files:
        return None

    selector = setup_selector.strip()

    if selector.lower() == "auto":
        # Prefer common variants first.
        by_name = {p.name.lower(): p for p in setup_files}
        for key in DEFAULT_SETUP_PRIORITY:
            target = f"setup_{key}.json".lower()
            if target in by_name:
                return by_name[target]
        return setup_files[0]

    # Allow passing full filename like "setup_ek.json".
    if selector.lower().startswith("setup_") and selector.lower().endswith(".json"):
        for p in setup_files:
            if p.name.lower() == selector.lower():
                return p
        return None

    # Allow passing short role like "ek" / "mage".
    target = f"setup_{selector}.json".lower()
    for p in setup_files:
        if p.name.lower() == target:
            return p

    return None


def _derive_refill_options_from_setup(setup: Dict[str, Any]) -> Dict[str, Any]:
    hunt_cfg = setup.get("hunt_config") if isinstance(setup, dict) else None
    hunt_cfg = hunt_cfg if isinstance(hunt_cfg, dict) else {}

    mana_name_raw = hunt_cfg.get("mana_name")
    if not isinstance(mana_name_raw, str) or not mana_name_raw.strip():
        mana_name_raw = "Mana Potion"
    mana_name = MANA_POTION_CANONICAL.get(mana_name_raw.strip().lower(), mana_name_raw)

    take_mana = _safe_int(hunt_cfg.get("take_mana"))

    # Health potions are not derivable reliably from legacy setups (varies a lot).
    # Keep required keys to avoid runtime KeyErrors.
    return {
        "healthPotionEnabled": False,
        "houseNpcEnabled": False,
        "healthPotion": {"item": "Health Potion", "quantity": 0},
        "manaPotion": {"item": mana_name, "quantity": max(0, take_mana)},
    }


def _derive_refill_checker_base_from_setup(setup: Dict[str, Any]) -> Dict[str, Any]:
    hunt_cfg = setup.get('hunt_config') if isinstance(setup, dict) else None
    hunt_cfg = hunt_cfg if isinstance(hunt_cfg, dict) else {}

    # Legacy setups usually have:
    # - mana_leave: minimum mana potions to continue hunting
    # - cap_leave: minimum cap to continue hunting
    mana_leave = _safe_int(hunt_cfg.get('mana_leave'))
    cap_leave = _safe_int(hunt_cfg.get('cap_leave'))

    return {
        'minimumAmountOfHealthPotions': 0,
        'minimumAmountOfManaPotions': max(0, mana_leave),
        'minimumAmountOfCap': max(0, cap_leave),
        'healthEnabled': False,
        # to be filled per-waypoint
        'waypointLabelToRedirect': '',
    }


def _default_refill_options() -> Dict[str, Any]:
    return {
        'healthPotionEnabled': False,
        'houseNpcEnabled': False,
        'healthPotion': {'item': 'Health Potion', 'quantity': 0},
        'manaPotion': {'item': 'Mana Potion', 'quantity': 0},
    }


def _normalize_refill_waypoint_options_in_place(waypoints: List[Dict[str, Any]]) -> int:
    changed = 0
    for wp in waypoints:
        if not isinstance(wp, dict) or wp.get('type') != 'refill':
            continue
        opts = wp.get('options')
        if not isinstance(opts, dict):
            continue
        mana = opts.get('manaPotion')
        health = opts.get('healthPotion')

        if isinstance(mana, dict):
            item = mana.get('item')
            if isinstance(item, str):
                normalized = MANA_POTION_CANONICAL.get(item.strip().lower())
                if normalized and normalized != item:
                    mana['item'] = normalized
                    changed += 1

        if isinstance(health, dict):
            item = health.get('item')
            if isinstance(item, str):
                normalized = HEALTH_POTION_CANONICAL.get(item.strip().lower())
                if normalized and normalized != item:
                    health['item'] = normalized
                    changed += 1

        # Make "sell empties then buy" explicit, but keep it optional.
        if 'sellFlasksBeforeRefill' not in opts:
            opts['sellFlasksBeforeRefill'] = True
            changed += 1

        # Default allow-list (strict) for the pre-refill sell step.
        if 'sellableItems' not in opts:
            opts['sellableItems'] = ['empty potion flask', 'empty vial']
            changed += 1

    return changed


def _normalize_sell_flasks_waypoint_options_in_place(waypoints: List[Dict[str, Any]]) -> int:
    changed = 0
    for wp in waypoints:
        if not isinstance(wp, dict) or wp.get('type') != 'sellFlasks':
            continue
        opts = wp.get('options')
        if not isinstance(opts, dict):
            continue
        if 'action' in opts:
            opts.pop('action', None)
            changed += 1

        # Many converted scripts carry a placeholder note.
        note = opts.get('note')
        if isinstance(note, str) and note.strip().lower() == 'unsupported':
            opts.pop('note', None)
            changed += 1

        # Make the allowed items explicit (still strict allow-list).
        if 'sellableItems' not in opts:
            opts['sellableItems'] = ['empty potion flask', 'empty vial']
            changed += 1
    return changed


def _merge_sellable_items(existing: Any, extra: Any) -> List[str]:
    base: List[str] = []
    if isinstance(existing, list):
        base = [x for x in existing if isinstance(x, str) and x]
    add: List[str] = []
    if isinstance(extra, list):
        add = [x for x in extra if isinstance(x, str) and x]

    seen = set()
    out: List[str] = []
    for x in base + add:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _dedupe_sellflasks_into_refill_in_place(waypoints: List[Dict[str, Any]]) -> int:
    """If a `sellFlasks` waypoint targets the same coordinate as a `refill` waypoint,
    merge its options into the refill and remove the redundant sellFlasks waypoint.

    This keeps selling strictly allow-listed, but avoids doing two separate waypoints
    when the intent is: sell empties then buy potions at the same NPC.
    """

    def _coord_key(wp: Dict[str, Any]) -> Optional[Tuple[int, int, int]]:
        c = wp.get('coordinate')
        if (
            isinstance(c, list)
            and len(c) == 3
            and all(isinstance(v, int) for v in c)
        ):
            return (c[0], c[1], c[2])
        return None

    refill_indexes_by_coord: Dict[Tuple[int, int, int], List[int]] = {}
    for idx, wp in enumerate(waypoints):
        if not isinstance(wp, dict) or wp.get('type') != 'refill':
            continue
        key = _coord_key(wp)
        if key is None:
            continue
        refill_indexes_by_coord.setdefault(key, []).append(idx)

    if not refill_indexes_by_coord:
        return 0

    removed = 0
    new_waypoints: List[Dict[str, Any]] = []

    for idx, wp in enumerate(waypoints):
        if not isinstance(wp, dict) or wp.get('type') != 'sellFlasks':
            if isinstance(wp, dict):
                new_waypoints.append(wp)
            continue

        key = _coord_key(wp)
        if key is None:
            new_waypoints.append(wp)
            continue

        refill_idxs = refill_indexes_by_coord.get(key)
        if not refill_idxs:
            new_waypoints.append(wp)
            continue

        # Prefer the next refill after this sellFlasks, otherwise fallback to the closest earlier refill.
        target_idx: Optional[int] = None
        for ridx in refill_idxs:
            if ridx > idx:
                target_idx = ridx
                break
        if target_idx is None:
            target_idx = refill_idxs[-1]

        try:
            target_refill = waypoints[target_idx]
            sell_opts = wp.get('options')
            if not isinstance(sell_opts, dict):
                sell_opts = {}

            refill_opts = target_refill.get('options') if isinstance(target_refill, dict) else None
            if not isinstance(refill_opts, dict):
                refill_opts = {}
                if isinstance(target_refill, dict):
                    target_refill['options'] = refill_opts

            # Ensure selling step is enabled inside refill.
            if 'sellFlasksBeforeRefill' not in refill_opts:
                refill_opts['sellFlasksBeforeRefill'] = True

            # Merge allow-list + tuning options (do not overwrite existing values).
            if 'sellableItems' not in refill_opts:
                refill_opts['sellableItems'] = sell_opts.get('sellableItems', ['empty potion flask', 'empty vial'])
            else:
                refill_opts['sellableItems'] = _merge_sellable_items(refill_opts.get('sellableItems'), sell_opts.get('sellableItems'))

            for k in (
                'amountPerStack',
                'maxSlotsToScan',
                'maxNoTradeRetries',
                'maxNoScreenshotRetries',
                'maxConsecutiveUnknownSlots',
            ):
                if k not in refill_opts and k in sell_opts:
                    refill_opts[k] = sell_opts[k]

            # Drop redundant sellFlasks waypoint.
            removed += 1
            continue
        except Exception:
            # Best-effort: if anything looks odd, keep the original waypoint.
            new_waypoints.append(wp)
            continue

    if removed:
        waypoints[:] = new_waypoints

    return removed


def _remove_sellflasks_if_refill_present_in_place(waypoints: List[Dict[str, Any]]) -> int:
    """If the route already has a refill step, remove standalone sellFlasks waypoints.

    Rationale: refill now sells empty containers before buying potions, so keeping
    separate sellFlasks steps is redundant and can cause double-selling / extra loops.
    """

    has_refill = any(isinstance(wp, dict) and wp.get('type') == 'refill' for wp in waypoints)
    if not has_refill:
        return 0

    removed = 0
    new_waypoints: List[Dict[str, Any]] = []
    for wp in waypoints:
        if isinstance(wp, dict) and wp.get('type') == 'sellFlasks':
            removed += 1
            continue
        if isinstance(wp, dict):
            new_waypoints.append(wp)

    if removed:
        waypoints[:] = new_waypoints
    return removed


def _upgrade_waypoints_in_place(
    waypoints: List[Dict[str, Any]],
    refill_options: Dict[str, Any],
) -> Tuple[int, int]:
    converted = 0
    skipped = 0

    for wp in waypoints:
        if not isinstance(wp, dict):
            continue

        wp_type = wp.get("type")
        options = wp.get("options")
        if not (wp_type == "walk" and isinstance(options, dict)):
            continue

        action = options.get("action")
        if action != "buy_potions":
            continue

        # Convert marker into real refill waypoint.
        wp["type"] = "refill"
        wp["options"] = refill_options
        wp["ignore"] = False
        converted += 1

    return converted, skipped


def _find_next_nonempty_label(waypoints: List[Dict[str, Any]], start_index: int) -> Optional[str]:
    for wp in waypoints[start_index + 1:]:
        if not isinstance(wp, dict):
            continue
        label = wp.get('label')
        if isinstance(label, str) and label.strip():
            return label.strip()
    return None


def _upgrade_check_supplies_in_place(
    waypoints: List[Dict[str, Any]],
    checker_base: Dict[str, Any],
) -> Tuple[int, int]:
    converted = 0
    skipped = 0

    for idx, wp in enumerate(waypoints):
        if not isinstance(wp, dict):
            continue

        wp_type = wp.get('type')
        options = wp.get('options')
        if not (wp_type == 'walk' and isinstance(options, dict)):
            continue

        action = options.get('action')
        if action not in {'check_supplies', 'check'}:
            continue

        next_label = _find_next_nonempty_label(waypoints, idx)
        if not next_label:
            skipped += 1
            continue

        wp['type'] = 'refillChecker'
        wp['ignore'] = False
        merged = dict(checker_base)
        merged['waypointLabelToRedirect'] = next_label
        wp['options'] = merged
        converted += 1

    return converted, skipped


def _upgrade_sell_in_place(waypoints: List[Dict[str, Any]]) -> Tuple[int, int]:
    converted = 0
    skipped = 0

    for wp in waypoints:
        if not isinstance(wp, dict):
            continue

        wp_type = wp.get('type')
        options = wp.get('options')
        if not (wp_type == 'walk' and isinstance(options, dict)):
            continue

        action = options.get('action')
        if action != 'sell':
            continue

        # We only support selling empty potion flasks for now.
        wp['type'] = 'sellFlasks'
        wp['ignore'] = False
        cleaned = dict(options)
        cleaned.pop('action', None)
        wp['options'] = cleaned
        converted += 1

    return converted, skipped


def _iter_waypoint_files() -> Iterable[Path]:
    # Only convert waypoint routes; skip general helper scripts like refill_*.pilotscript.
    yield from sorted(SCRIPTS_CONVERTED.glob("**/waypoints*.pilotscript"))


def convert_file(path: Path, setup_selector: str, dry_run: bool, backup: bool) -> FileResult:
    rel = path.relative_to(SCRIPTS_CONVERTED)
    rel_dir = rel.parent

    try:
        payload = _load_json(path)
    except Exception as e:
        return FileResult(
            path=str(rel).replace('\\', '/'),
            modified=False,
            converted_buy_potions=0,
            converted_check_supplies=0,
            converted_sell=0,
            skipped_buy_potions=0,
            skipped_check_supplies=0,
            skipped_sell=0,
            setup_used=None,
            reason=f"failed to parse JSON: {e}",
        )

    if not isinstance(payload, list):
        return FileResult(
            path=str(rel).replace('\\', '/'),
            modified=False,
            converted_buy_potions=0,
            converted_check_supplies=0,
            converted_sell=0,
            skipped_buy_potions=0,
            skipped_check_supplies=0,
            skipped_sell=0,
            setup_used=None,
            reason='unexpected schema (expected list of waypoints)',
        )

    normalized_refill_items = _normalize_refill_waypoint_options_in_place(payload)
    normalized_sell_flasks = _normalize_sell_flasks_waypoint_options_in_place(payload)
    merged_sellflasks_into_refill = _dedupe_sellflasks_into_refill_in_place(payload)
    removed_sellflasks = _remove_sellflasks_if_refill_present_in_place(payload)

    has_buy_potions = any(
        isinstance(wp, dict)
        and wp.get('type') == 'walk'
        and isinstance(wp.get('options'), dict)
        and wp.get('options', {}).get('action') == 'buy_potions'
        for wp in payload
    )

    has_check_supplies = any(
        isinstance(wp, dict)
        and wp.get('type') == 'walk'
        and isinstance(wp.get('options'), dict)
        and wp.get('options', {}).get('action') in {'check_supplies', 'check'}
        for wp in payload
    )

    has_sell = any(
        isinstance(wp, dict)
        and wp.get('type') == 'walk'
        and isinstance(wp.get('options'), dict)
        and wp.get('options', {}).get('action') == 'sell'
        for wp in payload
    )

    if not has_buy_potions and not has_check_supplies and not has_sell:
        if (
            normalized_refill_items > 0
            or normalized_sell_flasks > 0
            or merged_sellflasks_into_refill > 0
            or removed_sellflasks > 0
        ) and not dry_run:
            if backup:
                bak = path.with_suffix(path.suffix + '.bak')
                if not bak.exists():
                    bak.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
            _dump_json(path, payload)
        return FileResult(
            path=str(rel).replace('\\', '/'),
            modified=((normalized_refill_items > 0 or normalized_sell_flasks > 0 or merged_sellflasks_into_refill > 0 or removed_sellflasks > 0) and not dry_run),
            converted_buy_potions=0,
            converted_check_supplies=0,
            converted_sell=0,
            skipped_buy_potions=0,
            skipped_check_supplies=0,
            skipped_sell=0,
            setup_used=None,
            reason=(
                None
                if (normalized_refill_items == 0 and normalized_sell_flasks == 0 and merged_sellflasks_into_refill == 0 and removed_sellflasks == 0)
                else (
                    f"merged {merged_sellflasks_into_refill} sellFlasks into refill"
                    if (
                        merged_sellflasks_into_refill > 0
                        and removed_sellflasks == 0
                        and normalized_refill_items == 0
                        and normalized_sell_flasks == 0
                    )
                    else (
                        f"normalized {normalized_refill_items} refill item name(s)"
                        if (
                            normalized_refill_items > 0
                            and normalized_sell_flasks == 0
                            and merged_sellflasks_into_refill == 0
                            and removed_sellflasks == 0
                        )
                        else (
                            f"normalized {normalized_sell_flasks} sellFlasks option(s)"
                            if (
                                normalized_sell_flasks > 0
                                and normalized_refill_items == 0
                                and merged_sellflasks_into_refill == 0
                                and removed_sellflasks == 0
                            )
                            else (
                                (
                                    f"removed {removed_sellflasks} sellFlasks (refill handles selling now)"
                                    if (removed_sellflasks > 0 and merged_sellflasks_into_refill == 0 and normalized_refill_items == 0 and normalized_sell_flasks == 0)
                                    else (
                                        f"removed {removed_sellflasks} sellFlasks; merged {merged_sellflasks_into_refill}; normalized {normalized_refill_items} refill item name(s) and {normalized_sell_flasks} sellFlasks option(s)"
                                        if removed_sellflasks > 0
                                        else (
                                            f"normalized {normalized_refill_items} refill item name(s) and {normalized_sell_flasks} sellFlasks option(s)"
                                            if merged_sellflasks_into_refill == 0
                                            else f"merged {merged_sellflasks_into_refill} sellFlasks into refill; normalized {normalized_refill_items} refill item name(s) and {normalized_sell_flasks} sellFlasks option(s)"
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
        )

    # Setup selection (needed for check_supplies thresholds and optionally for refill).
    setup_files = _find_setup_files_for_rel_dir(rel_dir)
    picked = _pick_setup_file(setup_files, setup_selector)

    setup_used: Optional[str] = picked.name if picked is not None else None

    refill_options: Dict[str, Any]
    checker_base: Optional[Dict[str, Any]]

    if picked is None:
        existing = _get_existing_refill_options(payload)
        refill_options = existing if existing is not None else _default_refill_options()
        checker_base = None
    else:
        try:
            setup_payload = _load_json(picked)
        except Exception as e:
            return FileResult(
                path=str(rel).replace('\\', '/'),
                modified=False,
                converted_buy_potions=0,
                converted_check_supplies=0,
                converted_sell=0,
                skipped_buy_potions=0,
                skipped_check_supplies=0,
                skipped_sell=0,
                setup_used=picked.name,
                reason=f"failed to parse setup JSON ({picked.name}): {e}",
            )

        if not isinstance(setup_payload, dict):
            return FileResult(
                path=str(rel).replace('\\', '/'),
                modified=False,
                converted_buy_potions=0,
                converted_check_supplies=0,
                converted_sell=0,
                skipped_buy_potions=0,
                skipped_check_supplies=0,
                skipped_sell=0,
                setup_used=picked.name,
                reason=f"unexpected setup schema in {picked.name} (expected dict)",
            )

        refill_options = _derive_refill_options_from_setup(setup_payload)
        checker_base = _derive_refill_checker_base_from_setup(setup_payload)

    converted_buy, skipped_buy = (0, 0)
    if has_buy_potions:
        converted_buy, skipped_buy = _upgrade_waypoints_in_place(payload, refill_options)

    converted_check, skipped_check = (0, 0)
    if has_check_supplies:
        if checker_base is None:
            # Without a setup file we cannot safely infer thresholds.
            skipped_check = sum(
                1
                for wp in payload
                if isinstance(wp, dict)
                and wp.get('type') == 'walk'
                and isinstance(wp.get('options'), dict)
                and wp.get('options', {}).get('action') in {'check_supplies', 'check'}
            )
        else:
            converted_check, skipped_check = _upgrade_check_supplies_in_place(payload, checker_base)

    converted_sell, skipped_sell = (0, 0)
    if has_sell:
        converted_sell, skipped_sell = _upgrade_sell_in_place(payload)

    if (
        converted_buy <= 0
        and converted_check <= 0
        and converted_sell <= 0
        and normalized_refill_items <= 0
        and normalized_sell_flasks <= 0
        and merged_sellflasks_into_refill <= 0
        and removed_sellflasks <= 0
    ):
        reason: Optional[str] = None
        if has_check_supplies and checker_base is None:
            reason = 'check_supplies/check markers found but no matching setup_*.json in scripts-master'
        return FileResult(
            path=str(rel).replace('\\', '/'),
            modified=False,
            converted_buy_potions=0,
            converted_check_supplies=0,
            converted_sell=0,
            skipped_buy_potions=skipped_buy,
            skipped_check_supplies=skipped_check,
            skipped_sell=skipped_sell,
            setup_used=setup_used,
            reason=reason,
        )

    if not dry_run:
        if backup:
            bak = path.with_suffix(path.suffix + '.bak')
            if not bak.exists():
                bak.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        _dump_json(path, payload)

    return FileResult(
        path=str(rel).replace('\\', '/'),
        modified=not dry_run,
        converted_buy_potions=converted_buy,
        converted_check_supplies=converted_check,
        converted_sell=converted_sell,
        skipped_buy_potions=skipped_buy,
        skipped_check_supplies=skipped_check,
        skipped_sell=skipped_sell,
        setup_used=setup_used,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--setup",
        default="auto",
        help=(
            "Which setup to use per folder. "
            "Use 'auto' (default), a short role like 'mage'/'ek'/'rp', "
            "or an exact filename like 'setup_ek.json'."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write files; only report what would change.")
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Disable writing .bak backups when modifying files.",
    )
    parser.add_argument(
        "--report",
        default=str(SCRIPTS_CONVERTED / "legacy_actions_migration_report.json"),
        help="Where to write a JSON report.",
    )

    args = parser.parse_args()

    results: List[FileResult] = []
    for file_path in _iter_waypoint_files():
        results.append(
            convert_file(
                file_path,
                setup_selector=str(args.setup),
                dry_run=bool(args.dry_run),
                backup=not bool(args.no_backup),
            )
        )

    def _is_error_reason(reason: Optional[str]) -> bool:
        if not reason:
            return False
        lowered = reason.lower()
        return lowered.startswith('failed') or lowered.startswith('unexpected')

    def _is_note_reason(reason: Optional[str]) -> bool:
        return bool(reason) and not _is_error_reason(reason)

    summary = {
        "setup_selector": str(args.setup),
        "dry_run": bool(args.dry_run),
        "files_total": len(results),
        "files_modified_total": sum(1 for r in results if r.modified),
        "files_with_changes": sum(1 for r in results if r.converted_buy_potions > 0 and r.modified),
        "files_would_change": sum(1 for r in results if r.converted_buy_potions > 0 and not r.modified),
        "buy_potions_converted": sum(r.converted_buy_potions for r in results),
        "check_supplies_converted": sum(r.converted_check_supplies for r in results),
        "sell_converted": sum(r.converted_sell for r in results),
        "errors": [
            {
                "path": r.path,
                "reason": r.reason,
                "setup_used": r.setup_used,
            }
            for r in results
            if _is_error_reason(r.reason)
        ],
        "notes": [
            {
                "path": r.path,
                "note": r.reason,
            }
            for r in results
            if _is_note_reason(r.reason)
        ],
        "files": [r.__dict__ for r in results],
    }

    report_path = Path(str(args.report))
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Print a concise summary for terminal usage.
    print(json.dumps({k: summary[k] for k in [
        "setup_selector",
        "dry_run",
        "files_total",
        "files_modified_total",
        "files_with_changes",
        "files_would_change",
        "buy_potions_converted",
        "check_supplies_converted",
        "sell_converted",
        "errors",
        "notes",
    ]}, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
