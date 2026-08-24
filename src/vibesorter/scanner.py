from __future__ import annotations

from pathlib import Path

from PIL import Image

# Pillow's registered extensions reflect the formats actually available in the
# installed Pillow build. This is safer than maintaining a hand-written list.
IMAGE_EXTENSIONS = frozenset(Image.registered_extensions())


def find_images(folder: str | Path, *, recursive: bool = True) -> list[Path]:
    """Return Pillow-supported image files below *folder*, sorted by path.

    Discovery is deliberately extension-based; the image is opened later so a
    corrupt file can be reported without making scanning itself expensive.
    """
    root = Path(folder).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    iterator = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (path for path in iterator if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: str(path).casefold(),
    )
