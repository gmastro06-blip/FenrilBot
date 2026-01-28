import pathlib
from typing import Any

import numpy as np
from src.utils.core import hashit
from src.utils.image import loadFromRGBToGray


currentPath = pathlib.Path(__file__).parent.resolve()
imagesPath = f'{currentPath}/images'
containersBarsImagesPath = f'{imagesPath}/containersBars'
slotsImagesPath = f'{imagesPath}/slots'


def _load_optional(path: str) -> np.ndarray[Any, Any] | None:
    try:
        if pathlib.Path(path).exists():
            return loadFromRGBToGray(path)
    except Exception:
        return None
    return None


def _add_optional_slot_image(images_dict: dict, slot_key: str, filename: str) -> None:
    try:
        img = _load_optional(f'{slotsImagesPath}/{filename}')
        if img is not None:
            images_dict['slots'][slot_key] = img
    except Exception:
        # Best-effort: optional images should never break startup.
        return


def _add_optional_slot_hashes(
    images_dict: dict,
    *,
    filename_prefix: str,
    canonical_name: str,
    hashes_dict: dict,
) -> None:
    try:
        slots_dir = pathlib.Path(slotsImagesPath)
        for file in slots_dir.glob(f'{filename_prefix}*.png'):
            try:
                img = _load_optional(str(file))
                if img is None:
                    continue
                # Keep a reference for debugging / future reuse.
                images_dict['slots'][file.stem] = img
                hashes_dict[hashit(img)] = canonical_name
            except Exception:
                continue
    except Exception:
        return


def _add_optional_templates_from_dir(images_dict: dict, *, dir_path: str, bucket: str) -> None:
    """Load any extra *.png templates from a directory.

    This lets users add new templates (e.g. 'Camouflage Backpack v2.png')
    without requiring code changes.
    """
    try:
        p = pathlib.Path(dir_path)
        if not p.exists():
            return
        for file in p.glob('*.png'):
            try:
                key = file.stem
                if key in images_dict.get(bucket, {}):
                    continue
                img = _load_optional(str(file))
                if img is None:
                    continue
                images_dict[bucket][key] = img
            except Exception:
                continue
    except Exception:
        return

images = {
    'containersBars': {
        'backpack bottom': loadFromRGBToGray(f'{containersBarsImagesPath}/backpack bottom.png'),
        '25 Years Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/25 Years Backpack.png'),
        'Anniversary Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Anniversary Backpack.png'),
        'Beach Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Beach Backpack.png'),
        'Birthday Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Birthday Backpack.png'),
        'Brocade Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Brocade Backpack.png'),
        'Buggy Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Buggy Backpack.png'),
        'Cake Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Cake Backpack.png'),
        'Camouflage Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Camouflage Backpack.png'),
        'Crown Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Crown Backpack.png'),
        'Crystal Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Crystal Backpack.png'),
        'Deepling Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Deepling Backpack.png'),
        'Demon Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Demon Backpack.png'),
        'Dragon Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Dragon Backpack.png'),
        'Expedition Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Expedition Backpack.png'),
        'Fur Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Fur Backpack.png'),
        'Glooth Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Glooth Backpack.png'),
        'Golden Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Golden Backpack.png'),
        'Green Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Green Backpack v2.png'),
        'Heart Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Heart Backpack.png'),
        'locker': loadFromRGBToGray(f'{containersBarsImagesPath}/locker.png'),
        'Minotaur Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Minotaur Backpack.png'),
        'Moon Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Moon Backpack.png'),
        'Mushroom Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Mushroom Backpack.png'),
        'Pannier Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Pannier Backpack.png'),
        'Pirate Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Pirate Backpack.png'),
        'Raccoon Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Raccoon Backpack.png'),
        'Red Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Red Backpack v2..png'),
        'Santa Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Santa Backpack.png'),
        'Wolf Backpack': loadFromRGBToGray(f'{containersBarsImagesPath}/Wolf Backpack.png'),
    },
    'slots': {
        '25 Years Backpack': loadFromRGBToGray(f'{slotsImagesPath}/25 Years Backpack.png'),
        'Anniversary Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Anniversary Backpack.png'),
        'Beach Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Beach Backpack.png'),
        'big empty potion flask': loadFromRGBToGray(f'{slotsImagesPath}/big empty potion flask.png'),
        'Birthday Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Birthday Backpack.png'),
        'Brocade Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Brocade Backpack.png'),
        'Buggy Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Buggy Backpack.png'),
        'Camouflage Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Camouflage Backpack.png'),
        'Crown Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Crown Backpack.png'),
        'Crystal Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Crystal Backpack.png'),
        'Deepling Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Deepling Backpack.png'),
        'Demon Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Demon Backpack.png'),
        'depot': loadFromRGBToGray(f'{slotsImagesPath}/depot.png'),
        'depot chest 1': loadFromRGBToGray(f'{slotsImagesPath}/depot chest 1.png'),
        'depot chest 2': loadFromRGBToGray(f'{slotsImagesPath}/depot chest 2.png'),
        'depot chest 3': loadFromRGBToGray(f'{slotsImagesPath}/depot chest 3.png'),
        'depot chest 4': loadFromRGBToGray(f'{slotsImagesPath}/depot chest 4.png'),
        'Dragon Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Dragon Backpack.png'),
        'empty': loadFromRGBToGray(f'{slotsImagesPath}/empty.png'),
        'Expedition Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Expedition Backpack.png'),
        'Fur Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Fur Backpack.png'),
        'Glooth Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Glooth Backpack.png'),
        'Heart Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Heart Backpack.png'),
        'medium empty potion flask': loadFromRGBToGray(f'{slotsImagesPath}/medium empty potion flask.png'),
        'Minotaur Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Minotaur Backpack.png'),
        'Moon Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Moon Backpack.png'),
        'Mushroom Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Mushroom Backpack.png'),
        'Pannier Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Pannier Backpack.png'),
        'Pirate Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Pirate Backpack.png'),
        'Raccoon Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Raccoon Backpack.png'),
        'Santa Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Santa Backpack.png'),
        'small empty potion flask': loadFromRGBToGray(f'{slotsImagesPath}/small empty potion flask.png'),
        'stash': loadFromRGBToGray(f'{slotsImagesPath}/stash.png'),
        'Wolf Backpack': loadFromRGBToGray(f'{slotsImagesPath}/Wolf Backpack.png'),
    }
}

slotsImagesHashes = {
    hashit(images['slots']['big empty potion flask']): 'empty potion flask',
    hashit(images['slots']['medium empty potion flask']): 'empty potion flask',
    hashit(images['slots']['small empty potion flask']): 'empty potion flask',
    hashit(images['slots']['empty']): 'empty slot',
}

# Optional slot templates (safe if missing). Any file matching `empty vial*.png` will be mapped.
_add_optional_slot_hashes(
    images,
    filename_prefix='empty vial',
    canonical_name='empty vial',
    hashes_dict=slotsImagesHashes,
)

# Load any additional templates added by the user.
_add_optional_templates_from_dir(images, dir_path=slotsImagesPath, bucket='slots')
_add_optional_templates_from_dir(images, dir_path=containersBarsImagesPath, bucket='containersBars')
