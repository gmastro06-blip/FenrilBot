from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import numpy as np

from src.shared.typings import GrayImage
from src.repositories.inventory.core import images as inventory_images
from src.utils.core import getScreenshot, locate, setScreenshotOutputIdx
from src.utils.image import save as save_gray


@dataclass(frozen=True)
class SlotTemplateCaptureResult:
    slot_index: int
    out_path: Path
    item_name: Optional[str]
    image_shape: tuple[int, int]


class SlotTemplateCapturer:
    """Capture inventory-slot PNG templates at the exact size the bot expects.

    The bot's inventory recognition uses hashing of a fixed-size grayscale crop.
    If you capture icons manually with the wrong size, hashes won't match.

    This helper extracts slot crops using the same grid math used by gameplay tasks.

    Typical workflow
    - Open your main backpack in-game (4 columns grid).
    - Put the items you want to capture into the first slots (0, 1, 2, ...).
    - Run a script that calls this class (see scripts/capture_slot_templates.py).
    """

    def __init__(
        self,
        backpack: str,
        *,
        out_dir: Path | str,
        slot_width: int = 32,
        slot_height: int = 21,
        slot_stride_x: int = 32,
        slot_stride_y: int = 32,
        slot_gap_x: int = 5,
        slot_gap_y: int = 5,
        grid_columns: int = 4,
        anchor_offset_x: int = 10,
        anchor_offset_y: int = 18,
        capture_region: Optional[tuple[int, int, int, int]] = None,
        capture_absolute_region: Optional[tuple[int, int, int, int]] = None,
        output_idx: Optional[int] = None,
    ) -> None:
        self.backpack = backpack
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.slot_width = int(slot_width)
        self.slot_height = int(slot_height)
        self.slot_stride_x = int(slot_stride_x)
        self.slot_stride_y = int(slot_stride_y)
        self.slot_gap_x = int(slot_gap_x)
        self.slot_gap_y = int(slot_gap_y)
        self.grid_columns = int(grid_columns)

        # IMPORTANT: keep these defaults aligned with SellEachFlaskTask.getSlot() math.
        # locate() returns a bbox in (y, x, w, h) space in this codebase.
        self.anchor_offset_x = int(anchor_offset_x)
        self.anchor_offset_y = int(anchor_offset_y)

        self.capture_region = capture_region
        self.capture_absolute_region = capture_absolute_region
        self.output_idx = int(output_idx) if output_idx is not None else None

        if self.output_idx is not None:
            setScreenshotOutputIdx(self.output_idx)

    def grab_screenshot(self) -> Optional[GrayImage]:
        return getScreenshot(region=self.capture_region, absolute_region=self.capture_absolute_region)

    def _locate_backpack_bar(self, screenshot: GrayImage) -> Optional[tuple[int, int, int, int]]:
        template = inventory_images['containersBars'].get(self.backpack)
        if template is None:
            raise KeyError(f"Unknown backpack bar template: {self.backpack!r}")
        return locate(screenshot, template, confidence=0.8)

    def extract_slot(self, screenshot: GrayImage, slot_index: int) -> Optional[np.ndarray]:
        bar_pos = self._locate_backpack_bar(screenshot)
        if bar_pos is None:
            return None

        slot_x_index = int(slot_index) % self.grid_columns
        slot_y_index = int(slot_index) // self.grid_columns

        # Same math as SellEachFlaskTask.getSlot():
        # - bar_pos is (y, x, w, h)
        # - containerPositionX derives from x (bar_pos[1])
        # - containerPositionY derives from y (bar_pos[0])
        container_position_x = int(bar_pos[1]) + self.anchor_offset_y
        container_position_y = int(bar_pos[0]) + self.anchor_offset_x

        y0 = container_position_x + slot_y_index * self.slot_stride_y + slot_y_index * self.slot_gap_y
        y1 = y0 + self.slot_height
        x0 = container_position_y + slot_x_index * self.slot_stride_x + slot_x_index * self.slot_gap_x
        x1 = x0 + self.slot_width

        arr = np.asarray(screenshot)
        if y0 < 0 or x0 < 0 or y1 > arr.shape[0] or x1 > arr.shape[1]:
            return None

        crop = arr[y0:y1, x0:x1]
        # Ensure uint8 grayscale.
        return np.array(crop, dtype=np.uint8)

    def capture_to_files(
        self,
        *,
        prefix: str,
        slot_indices: Sequence[int],
        assume_item_name: Optional[str] = None,
        screenshot: Optional[GrayImage] = None,
    ) -> list[SlotTemplateCaptureResult]:
        if screenshot is None:
            screenshot = self.grab_screenshot()
        if screenshot is None:
            raise RuntimeError('Could not grab screenshot (capture backend returned None).')

        results: list[SlotTemplateCaptureResult] = []
        for i, slot_idx in enumerate(slot_indices, start=1):
            crop = self.extract_slot(screenshot, int(slot_idx))
            if crop is None:
                raise RuntimeError(
                    f'Could not extract slot {slot_idx}. Is the backpack open and visible in the capture window?'
                )
            out_path = self.out_dir / f'{prefix} {i}.png'
            save_gray(crop, str(out_path))
            results.append(
                SlotTemplateCaptureResult(
                    slot_index=int(slot_idx),
                    out_path=out_path,
                    item_name=assume_item_name,
                    image_shape=(int(crop.shape[0]), int(crop.shape[1])),
                )
            )
        return results

    def capture_first_n_nonempty(
        self,
        *,
        prefix: str,
        n: int,
        max_scan_slots: int = 120,
        empty_slot_hashes: Optional[Iterable[int]] = None,
    ) -> list[SlotTemplateCaptureResult]:
        """Capture the first N non-empty crops from the backpack grid.

        This is a convenience helper when you have items scattered; it still expects
        the backpack to be visible and uses the same crop size.

        If you pass `empty_slot_hashes`, those crops will be skipped.
        """
        from src.utils.core import hashit

        screenshot = self.grab_screenshot()
        if screenshot is None:
            raise RuntimeError('Could not grab screenshot (capture backend returned None).')

        empty_hash_set = set(empty_slot_hashes or [])
        written: list[SlotTemplateCaptureResult] = []

        for slot_idx in range(int(max_scan_slots)):
            if len(written) >= int(n):
                break
            crop = self.extract_slot(screenshot, slot_idx)
            if crop is None:
                continue
            try:
                h = hashit(crop)
            except Exception:
                h = None
            if h is not None and h in empty_hash_set:
                continue

            out_path = self.out_dir / f'{prefix} {len(written) + 1}.png'
            save_gray(crop, str(out_path))
            written.append(
                SlotTemplateCaptureResult(
                    slot_index=int(slot_idx),
                    out_path=out_path,
                    item_name=None,
                    image_shape=(int(crop.shape[0]), int(crop.shape[1])),
                )
            )

        if len(written) < int(n):
            raise RuntimeError(f'Captured only {len(written)}/{n} slots. Try placing items in early slots.')

        return written
