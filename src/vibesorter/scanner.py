from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

# Pillow's registered extensions reflect the formats available in the installed
# Pillow build. Files are discovered by extension and decoded during analysis.
IMAGE_EXTENSIONS = frozenset(Image.registered_extensions())
MANAGED_DIRECTORY_NAMES = frozenset({".vibesorter"})


def _raise_walk_error(error: OSError) -> None:
    """Fail clearly instead of silently returning a partial library scan."""
    raise error


def find_images(folder: str | Path, *, recursive: bool = True) -> list[Path]:
    """Return supported image paths in deterministic order.

    Hidden user folders are included. VibeSorter-managed directories and all
    symlinked files/directories are excluded. Permission and traversal errors
    are raised rather than silently producing an incomplete result. Corrupt
    files can still be discovered; the decoder reports them during analysis.
    """
    root = Path(folder).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    found: list[Path] = []
    if recursive:
        for current, directories, filenames in os.walk(
            root, followlinks=False, onerror=_raise_walk_error
        ):
            current_path = Path(current)
            directories[:] = sorted(
                name
                for name in directories
                if name.casefold() not in MANAGED_DIRECTORY_NAMES
                and not (current_path / name).is_symlink()
            )
            found.extend(
                current_path / filename
                for filename in filenames
                if not (current_path / filename).is_symlink()
                and (current_path / filename).is_file()
                and (current_path / filename).suffix.lower() in IMAGE_EXTENSIONS
            )
    else:
        found.extend(
            path
            for path in root.iterdir()
            if not path.is_symlink()
            and path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
            and path.parent.name.casefold() not in MANAGED_DIRECTORY_NAMES
        )

    return sorted(found, key=lambda path: str(path).casefold())
