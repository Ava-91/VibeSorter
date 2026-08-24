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


def find_near_duplicates(
    paths: list[Path],
    *,
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> list[tuple[Path, Path, int]]:
    """Find visually similar image pairs using perceptual-hash distance.

    A small Hamming distance means the resized grayscale structures are similar.
    This deliberately reports pairs rather than deleting or choosing a winner.
    """
    if max_distance < 0:
        raise ValueError("max_distance must be non-negative")

    hashed: list[tuple[Path, int]] = []
    for path in paths:
        try:
            hashed.append((path, perceptual_hash(path)))
        except (OSError, ValueError):
            continue

    matches: list[tuple[Path, Path, int]] = []
    for index, (left_path, left_hash) in enumerate(hashed):
        for right_path, right_hash in hashed[index + 1:]:
            distance = hamming_distance(left_hash, right_hash)
            if distance <= max_distance:
                matches.append((left_path, right_path, distance))
    return matches
