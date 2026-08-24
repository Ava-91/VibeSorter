from __future__ import annotations

from pathlib import Path

IMAGE_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"
})


def find_images(folder: str | Path, *, recursive: bool = True) -> list[Path]:
    """Return supported image files below *folder*, sorted by path.

    The scanner only discovers files; it never moves, renames, deletes, or edits them.
    """
    root = Path(folder).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    iterator = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (
            path
            for path in iterator
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )
