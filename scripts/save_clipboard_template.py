import argparse
from pathlib import Path

from PIL import Image, ImageGrab


def _grab_clipboard_image() -> Image.Image:
    data = ImageGrab.grabclipboard()
    if data is None:
        raise RuntimeError("Clipboard is empty or does not contain an image.")

    if isinstance(data, Image.Image):
        return data

    # On Windows, grabclipboard can also return a list of file paths.
    if isinstance(data, list) and data:
        p = Path(data[0])
        if p.exists():
            return Image.open(p)

    raise RuntimeError(f"Clipboard content is not an image (type={type(data)}).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Save the current clipboard image into the Fenril template folders. "
            "Tip: copy the small container bar image (e.g., 'Green Backpack') then run this script."
        )
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output PNG path (e.g., src/repositories/inventory/images/containersBars/Green Backpack v2.png)",
    )
    parser.add_argument(
        "--expect-width",
        type=int,
        default=None,
        help="If set, fails unless the clipboard image width matches.",
    )
    parser.add_argument(
        "--expect-height",
        type=int,
        default=None,
        help="If set, fails unless the clipboard image height matches.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if the output file already exists.",
    )
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not args.force:
        raise RuntimeError(f"Output already exists: {out_path} (use --force to overwrite)")

    img = _grab_clipboard_image()
    w, h = img.size
    print(f"Clipboard image size: {w}x{h}")

    if args.expect_width is not None and w != args.expect_width:
        raise RuntimeError(f"Expected width {args.expect_width} but got {w}")
    if args.expect_height is not None and h != args.expect_height:
        raise RuntimeError(f"Expected height {args.expect_height} but got {h}")

    # Keep exact pixels; just normalize mode for consistent PNG saving.
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")

    img.save(out_path, format="PNG")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
