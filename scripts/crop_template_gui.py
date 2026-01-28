"""Interactive crop helper for template PNGs.

Use this to quickly create new template images that match *your* Tibia client + OBS scaling.

Example (create a new containersBars variant):
  python scripts/crop_template_gui.py \
    --image debug/loot_debug_no_loot_backpack_20260127_142458.png \
    --out src/repositories/inventory/images/containersBars/"Camouflage Backpack v2".png \
    --grayscale

Controls
- Click+drag to select a rectangle.
- Press Enter to save the crop.
- Press Esc to quit.

Tip
- For container bars, select the same region size as existing templates (roughly 94x12).
- For slot icons, crop tightly around the icon.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageTk
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Missing dependency Pillow. Install with: pip install pillow. Error: {exc!r}")

import tkinter as tk


@dataclass
class CropState:
    x0: Optional[int] = None
    y0: Optional[int] = None
    x1: Optional[int] = None
    y1: Optional[int] = None
    rect: Optional[int] = None


def main() -> int:
    parser = argparse.ArgumentParser(description="GUI crop helper for inventory templates")
    parser.add_argument("--image", required=True, help="Input screenshot path")
    parser.add_argument("--out", required=True, help="Output PNG path")
    parser.add_argument("--grayscale", action="store_true", help="Convert the crop to grayscale before saving")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    in_path = Path(args.image)
    if not in_path.is_absolute():
        in_path = (repo / in_path).resolve()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (repo / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(in_path)

    root = tk.Tk()
    root.title(f"Crop: {in_path.name} -> {out_path.name}")

    # Canvas + image
    tk_img = ImageTk.PhotoImage(img)
    canvas = tk.Canvas(root, width=tk_img.width(), height=tk_img.height(), cursor="cross")
    canvas.pack()
    canvas.create_image(0, 0, anchor="nw", image=tk_img)

    info = tk.StringVar(value="Drag to select. Enter=save, Esc=quit, B=preset bar 94x12")
    info_label = tk.Label(root, textvariable=info, anchor="w")
    info_label.pack(fill="x")

    state = CropState()

    def on_down(evt: tk.Event) -> None:
        state.x0, state.y0 = int(evt.x), int(evt.y)
        state.x1, state.y1 = int(evt.x), int(evt.y)
        if state.rect is not None:
            canvas.delete(state.rect)
        state.rect = int(canvas.create_rectangle(evt.x, evt.y, evt.x, evt.y, outline="red", width=2))

    def on_move(evt: tk.Event) -> None:
        if state.x0 is None:
            return
        state.x1, state.y1 = int(evt.x), int(evt.y)
        if state.rect is not None and state.x0 is not None and state.y0 is not None and state.x1 is not None and state.y1 is not None:
            canvas.coords(state.rect, state.x0, state.y0, state.x1, state.y1)

        box = _current_box()
        if box is not None:
            w = box[2] - box[0]
            h = box[3] - box[1]
            info.set(f"Box={box} size={w}x{h} | Enter=save, Esc=quit, B=preset bar 94x12")

    def _current_box() -> Optional[Tuple[int, int, int, int]]:
        if state.x0 is None or state.x1 is None or state.y0 is None or state.y1 is None:
            return None
        x0, y0, x1, y1 = state.x0, state.y0, state.x1, state.y1
        left = min(x0, x1)
        top = min(y0, y1)
        right = max(x0, x1)
        bottom = max(y0, y1)
        if right - left < 2 or bottom - top < 2:
            return None
        return (left, top, right, bottom)

    def on_enter(_evt: Optional[tk.Event] = None) -> None:
        box = _current_box()
        if box is None:
            print("No crop selected.")
            return
        crop = img.crop(box)
        if args.grayscale:
            crop = crop.convert("L")
        crop.save(out_path, format="PNG")
        print(f"Saved: {out_path}")
        print(f"Box: {box} size={(box[2]-box[0], box[3]-box[1])}")
        root.destroy()

    def on_preset_bar(_evt: Optional[tk.Event] = None) -> None:
        # Tibia container bar templates are typically 94x12.
        if state.x0 is None or state.y0 is None:
            return
        x0, y0 = int(state.x0), int(state.y0)
        x1, y1 = x0 + 94, y0 + 12
        state.x1, state.y1 = x1, y1
        if state.rect is not None:
            canvas.coords(state.rect, x0, y0, x1, y1)
        info.set(f"Preset bar 94x12 at {(x0,y0)} | Enter=save, Esc=quit")

    def on_esc(_evt: Optional[tk.Event] = None) -> None:
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_down)
    canvas.bind("<B1-Motion>", on_move)
    root.bind("<Return>", on_enter)
    root.bind("<Escape>", on_esc)
    root.bind("b", on_preset_bar)
    root.bind("B", on_preset_bar)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
