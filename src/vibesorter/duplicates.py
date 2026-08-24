from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError


DEFAULT_HASH_SIZE = 8
DEFAULT_MAX_DISTANCE = 6


def content_hash(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return a stable SHA-256 hash of an image file's bytes."""
    image_path = Path(path).expanduser()
    digest = hashlib.sha256()
    with image_path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def find_exact_duplicates(paths: list[Path]) -> dict[str, list[Path]]:
    """Group files with identical bytes; groups contain only real duplicates."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        groups[content_hash(path)].append(path)
    return {digest: items for digest, items in groups.items() if len(items) > 1}


def perceptual_hash(path: str | Path, *, size: int = DEFAULT_HASH_SIZE) -> int:
    """Return a compact difference hash for visual near-duplicate matching."""
    if size < 2:
        raise ValueError("hash size must be at least 2")

    image_path = Path(path).expanduser()
    try:
        with Image.open(image_path) as source:
            image = source.convert("L").resize(
                (size + 1, size),
                Image.Resampling.LANCZOS,
            )
            pixels = list(image.getdata())
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupt image: {image_path}") from exc

    value = 0
    for row in range(size):
        offset = row * (size + 1)
        for column in range(size):
            value <<= 1
            value |= int(pixels[offset + column] > pixels[offset + column + 1])
    return value


def hamming_distance(left: int, right: int) -> int:
    """Count differing bits between two perceptual hashes."""
    return (left ^ right).bit_count()


class _BKTree:
    """Small metric index that avoids an O(n²) near-duplicate scan."""

    def __init__(self) -> None:
        self._root: tuple[int, list[Path], dict[int, "_BKTree"]] | None = None

    def add(self, value: int, path: Path) -> None:
        if self._root is None:
            self._root = (value, [path], {})
            return

        node = self._root
        while True:
            node_value, paths, children = node
            distance = hamming_distance(value, node_value)
            if distance == 0:
                paths.append(path)
                return
            child = children.get(distance)
            if child is None:
                child = _BKTree()
                children[distance] = child
                child._root = (value, [path], {})
                return
            node = child._root  # type: ignore[assignment]

    def query(self, value: int, radius: int) -> list[tuple[int, list[Path]]]:
        if self._root is None:
            return []
        matches: list[tuple[int, list[Path]]] = []
        self._query(self._root, value, radius, matches)
        return matches

    def _query(
        self,
        node: tuple[int, list[Path], dict[int, "_BKTree"]],
        value: int,
        radius: int,
        matches: list[tuple[int, list[Path]]],
    ) -> None:
        node_value, paths, children = node
        distance = hamming_distance(value, node_value)
        if distance <= radius:
            matches.append((node_value, paths))
        lower = max(0, distance - radius)
        upper = distance + radius
        for child_distance, child in children.items():
            if lower <= child_distance <= upper and child._root is not None:
                self._query(child._root, value, radius, matches)


def find_near_duplicates(
    paths: list[Path],
    *,
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> list[tuple[Path, Path, int]]:
    """Find visually similar image pairs using indexed perceptual hashes.

    Pairs at distance zero are omitted because exact duplicates are reported by
    ``find_exact_duplicates``. The BK-tree keeps this from becoming a full
    pairwise scan as collections grow.
    """
    if max_distance < 1:
        raise ValueError("max_distance must be at least 1")

    tree = _BKTree()
    matches: list[tuple[Path, Path, int]] = []
    hashed: list[tuple[Path, int]] = []

    for path in paths:
        try:
            hashed.append((path, perceptual_hash(path)))
        except (OSError, ValueError):
            continue

    for path, value in hashed:
        for matched_value, matched_paths in tree.query(value, max_distance):
            distance = hamming_distance(value, matched_value)
            if distance == 0:
                continue
            for matched_path in matched_paths:
                matches.append((matched_path, path, distance))
        tree.add(value, path)

    return sorted(matches, key=lambda item: (item[2], str(item[0]), str(item[1])))
