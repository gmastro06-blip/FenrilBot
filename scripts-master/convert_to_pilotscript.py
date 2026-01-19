import json
import pathlib
import re
from typing import Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT.parent / "scripts-converted"

COORD_RE = re.compile(r"\((\d+),\s*(\d+),\s*(\d+)\)")
RANDOM_RE = re.compile(r"\[(.*)\]")

CITY_MAP = {
    "abdendriel": "AbDendriel",
    "ankrahmun": "Ankrahmun",
    "carlin": "Carlin",
    "darashia": "Darashia",
    "edron": "Edron",
    "farmine": "Farmine",
    "issavi": "Issavi",
    "kazoordon": "Kazoordon",
    "kazordoon": "Kazoordon",
    "liberty_bay": "LibertBay",
    "port_hope": "PortHope",
    "rathleton": "Rathleton",
    "svargrond": "Svargrond",
    "thais": "Thais",
    "venore": "Venore",
    "yalahar": "Yalahar",
    "tibia": "Tibia",
    "peg_leg": "Peg Leg",
    "shortcut": "shortcut",
}

ACTION_TO_TYPE = {
    "deposit": "depositItems",
    "bank": "depositGold",
    "refill": "refill",
    "drop_vials": "dropFlasks",
}

SKIP_ACTIONS = {
    "end",
    "end_rashid",
    "exit",
    "quit",
    "repeat",
    "target_on",
    "target_off",
    "summon",
    "use_elevator",
    "walk_keys",
    "walk_mouse",
}

PLACEHOLDER_ACTIONS = {
    "sell",
    "buy_potions",
    "buy_runes",
    "buy_ammo",
    "buy_ticket",
    "buy_blessing",
    "stash_all",
    "wait",
    "levitate_north_up",
    "levitate_south_down",
    "levitate_up",
    "levitate_down",
    "levitate_east_down",
    "levitate_west_up",
}


def parse_coord(text: str) -> Optional[Tuple[int, int, int]]:
    match = COORD_RE.search(text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def parse_random_coords(text: str) -> List[Tuple[int, int, int]]:
    coords: List[Tuple[int, int, int]] = []
    match = RANDOM_RE.search(text)
    if not match:
        return coords
    content = match.group(1)
    for part in content.split("),"):
        coord = parse_coord(part + ")")
        if coord:
            coords.append(coord)
    return coords


def travel_city_from_action(action: str) -> Optional[str]:
    if not action.startswith("travel_"):
        return None
    key = action.replace("travel_", "").strip()
    return CITY_MAP.get(key, key.replace("_", " ").title().replace(" ", ""))


def make_waypoint(
    wtype: str,
    coord: Tuple[int, int, int],
    label: str = "",
    options: Optional[Dict] = None,
    ignore: bool = False,
    passinho: bool = False,
) -> Dict:
    return {
        "label": label,
        "type": wtype,
        "coordinate": [coord[0], coord[1], coord[2]],
        "options": options or {},
        "ignore": ignore,
        "passinho": passinho,
    }


def resolve_load_path(current_file: pathlib.Path, raw_path: str) -> pathlib.Path:
    raw_path = raw_path.strip().strip('"')
    if raw_path.startswith("scripts/"):
        raw_path = raw_path.replace("scripts/", "")
        return ROOT / raw_path
    return (current_file.parent / raw_path).resolve()


def convert_file(path: pathlib.Path, report: Dict) -> List[Dict]:
    waypoints: List[Dict] = []
    current_label = ""
    last_coord: Optional[Tuple[int, int, int]] = None

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        token, *rest = line.split(" ", 1)
        rest_text = rest[0] if rest else ""

        if token == "label":
            current_label = rest_text.strip()
            continue

        if token == "load":
            load_path = resolve_load_path(path, rest_text)
            if load_path.exists():
                waypoints.extend(convert_file(load_path, report))
            else:
                report.setdefault("missing_loads", []).append({
                    "file": str(path),
                    "load": rest_text,
                })
            continue

        if token == "call":
            report.setdefault("unsupported_calls", []).append({
                "file": str(path),
                "line": line,
            })
            continue

        if token == "random":
            coords = parse_random_coords(line)
            if coords:
                random_coord = coords[0]
                last_coord = random_coord
                waypoints.append(
                    make_waypoint("walk", random_coord, current_label, {}, True, False)
                )
                if len(coords) > 1:
                    report.setdefault("random_choices", []).append({
                        "file": str(path),
                        "line": line,
                        "used": random_coord,
                        "choices": coords,
                    })
                current_label = ""
            else:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
            continue

        coord = parse_coord(line)

        if token in {"node", "stand", "walk"}:
            if coord is None:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
                continue
            last_coord = coord
            ignore = token == "node"
            waypoints.append(make_waypoint("walk", coord, current_label, {}, ignore, False))
            current_label = ""
            continue

        if token == "door":
            if coord:
                last_coord = coord
                waypoints.append(make_waypoint("openDoor", coord, current_label, {}, False, False))
                current_label = ""
            else:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
            continue

        if token == "ladder":
            if coord:
                last_coord = coord
                waypoints.append(make_waypoint("useLadder", coord, current_label, {}, False, False))
                current_label = ""
            else:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
            continue

        if token == "rope":
            if coord:
                last_coord = coord
                waypoints.append(make_waypoint("useRope", coord, current_label, {}, False, False))
                current_label = ""
            else:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
            continue

        if token == "shovel":
            if coord:
                last_coord = coord
                waypoints.append(make_waypoint("useShovel", coord, current_label, {}, False, False))
                current_label = ""
            else:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
            continue

        if token == "use":
            if coord:
                last_coord = coord
                waypoints.append(make_waypoint("rightClickUse", coord, current_label, {}, False, False))
                current_label = ""
            else:
                report.setdefault("invalid_lines", []).append({
                    "file": str(path),
                    "line": line,
                })
            continue

        if token == "action":
            action = rest_text.strip()
            if not action:
                continue
            if action in SKIP_ACTIONS:
                report.setdefault("skipped_actions", []).append({
                    "file": str(path),
                    "action": action,
                })
                continue
            travel_city = travel_city_from_action(action)
            if travel_city and last_coord:
                waypoints.append(make_waypoint("travel", last_coord, current_label, {"city": travel_city}, False, False))
                current_label = ""
                continue
            if action in ACTION_TO_TYPE and last_coord:
                waypoints.append(make_waypoint(ACTION_TO_TYPE[action], last_coord, current_label, {}, False, False))
                current_label = ""
                continue
            if action in PLACEHOLDER_ACTIONS and last_coord:
                waypoints.append(
                    make_waypoint(
                        "walk",
                        last_coord,
                        current_label,
                        {"action": action, "note": "unsupported"},
                        True,
                        False,
                    )
                )
                report.setdefault("placeholder_actions", []).append({
                    "file": str(path),
                    "action": action,
                    "coordinate": last_coord,
                })
                current_label = ""
                continue

            if last_coord:
                waypoints.append(
                    make_waypoint(
                        "walk",
                        last_coord,
                        current_label,
                        {"action": action, "note": "unsupported"},
                        True,
                        False,
                    )
                )
                report.setdefault("placeholder_actions", []).append({
                    "file": str(path),
                    "action": action,
                    "coordinate": last_coord,
                })
                current_label = ""
                continue

            report.setdefault("unsupported_actions", []).append({
                "file": str(path),
                "action": action,
                "line": line,
            })
            continue

        report.setdefault("unsupported_lines", []).append({
            "file": str(path),
            "line": line,
        })

    return waypoints


def convert_all() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    report: Dict = {}

    for waypoint_file in ROOT.rglob("*.in"):
        rel_path = waypoint_file.relative_to(ROOT)
        output_file = OUTPUT_ROOT / rel_path.with_suffix(".pilotscript")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        waypoints = convert_file(waypoint_file, report)
        output_file.write_text(json.dumps(waypoints, indent=4), encoding="utf-8")

    report_file = OUTPUT_ROOT / "conversion_report.json"
    report_file.write_text(json.dumps(report, indent=4), encoding="utf-8")


if __name__ == "__main__":
    convert_all()
