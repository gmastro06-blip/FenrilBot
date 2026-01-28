from __future__ import annotations

import sys
from pathlib import Path


def _require_cv2() -> "object":
    try:
        import cv2  # type: ignore

        return cv2
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"Failed to import cv2 (opencv-python). Error: {exc!r}")


def _best_match(
    img: np.ndarray,
    tpl: np.ndarray,
    *,
    scales: list[float]
) -> tuple[float | None, float, tuple[int, int] | None, tuple[int, int] | None]:
    cv2 = _require_cv2()
    best: tuple[float | None, float, tuple[int, int] | None, tuple[int, int] | None] = (None, -1.0, None, None)  # scale, score, loc(x,y), tpl_shape
    for s in scales:
        if abs(s - 1.0) < 1e-9:
            t = tpl
        else:
            h, w = tpl.shape[:2]
            t = cv2.resize(tpl, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA)
        if t.shape[0] >= img.shape[0] or t.shape[1] >= img.shape[1]:
            continue
        res = cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED)
        _minv, maxv, _minloc, maxloc = cv2.minMaxLoc(res)
        if float(maxv) > best[1]:
            best = (s, float(maxv), (int(maxloc[0]), int(maxloc[1])), t.shape[:2])
    return best


def main(argv: list[str]) -> int:
    cv2 = _require_cv2()
    repo = Path(__file__).resolve().parents[1]

    img_path = repo / "debug" / "loot_debug_no_loot_backpack_20260127_142458.png"
    if len(argv) >= 2:
        img_path = Path(argv[1]).resolve()

    slot = "Camouflage Backpack"
    if len(argv) >= 3:
        slot = argv[2]

    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        print(f"Could not read image: {img_path}")
        return 2

    print("python", sys.version)
    print("cv2", cv2.__version__)
    print("image", img_path.name, img.shape)

    tpl_path = repo / "src" / "repositories" / "inventory" / "images" / "slots" / f"{slot}.png"
    tpl = cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE)
    if tpl is not None:
        scales = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30]
        s, score, loc, tshape = _best_match(img, tpl, scales=scales)
        print("template", slot, tpl.shape)
        print("best", {"scale": s, "score": score, "loc": loc, "tpl_shape": tshape})
    else:
        print("template", slot, f"(missing slots template: {tpl_path})")

    # Also check the container bar template for the same backpack (this is what loot uses).
    bar_path = repo / "src" / "repositories" / "inventory" / "images" / "containersBars" / f"{slot}.png"
    bar = cv2.imread(str(bar_path), cv2.IMREAD_GRAYSCALE)
    if bar is not None:
        sb, bar_score, bar_loc, bar_shape = _best_match(
            img,
            bar,
            scales=[0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30],
        )
        print("bar", slot, bar.shape)
        print("bar_best", {"scale": sb, "score": bar_score, "loc": bar_loc, "tpl_shape": bar_shape})
    else:
        print("bar", slot, "(missing template)")

    # Sanity check a couple other templates.
    for other in ["stash", "depot", "empty"]:
        p = repo / "src" / "repositories" / "inventory" / "images" / "slots" / f"{other}.png"
        t = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if t is None:
            continue
        s2, score2, loc2, tsh2 = _best_match(img, t, scales=[0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15])
        print("other", other, {"scale": s2, "score": score2, "loc": loc2, "tpl_shape": tsh2})

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
