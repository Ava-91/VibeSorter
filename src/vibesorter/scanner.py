from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

# Pillow's registered extensions reflect the formats actually available in the
# installed Pillow build. This is safer than maintaining a hand-written list.
IMAGE_EXTENSIONS = frozenset(Image.registered_extensions())
MANAGED_DIRECTORY_NAMES = frozenset({".vibesorter"})


def find_images(folder: str | Path, *, recursive: bool = True) -> list[Path]:
    """Return Pillow-supported image files below *folder*, sorted by path.

    Discovery is deliberately extension-based; the image is opened later so a
    corrupt file can be reported without making scanning itself expensive.
    VibeSorter-managed directories are pruned from traversal so generated
    thumbnails and other internal artifacts can never become source images.
    """
    root = Path(folder).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    found: list[Path] = []
    if recursive:
        for current, directories, filenames in os.walk(root, followlinks=False):
            # Prune before descent: besides avoiding generated files, this keeps
            # large application caches out of the scan entirely.
            directories[:] = sorted(
                name
                for name in directories
                if name.casefold() not in MANAGED_DIRECTORY_NAMES
            )
            current_path = Path(current)
            found.extend(
                current_path / filename
                for filename in filenames
                if (current_path / filename).is_file()
                and (current_path / filename).suffix.lower() in IMAGE_EXTENSIONS
            )
    else:
        found.extend(
            path
            for path in root.iterdir()
            if path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
            and path.parent.name.casefold() not in MANAGED_DIRECTORY_NAMES
        )

    return sorted(found, key=lambda path: str(path).casefold())
