from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from vibesorter.duplicates import find_exact_duplicates, find_near_duplicates, hamming_distance, perceptual_hash


def make_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (32, 32), color).save(path)


def test_hamming_distance_counts_different_bits() -> None:
    assert hamming_distance(0b1010, 0b1001) == 2


def test_exact_duplicates_group_identical_bytes(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    make_image(first, (30, 80, 180))
    second.write_bytes(first.read_bytes())

    groups = find_exact_duplicates([first, second])

    assert len(groups) == 1
    assert sorted(groups.values())[0] == [first, second]


def test_near_duplicates_find_similar_but_not_identical_images(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    image = Image.new("RGB", (80, 60), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 60, 45), fill="black")
    image.save(first)
    image.save(second)
    # Change one visual detail so the files are not byte-identical.
    changed = Image.open(second).convert("RGB")
    ImageDraw.Draw(changed).rectangle((50, 35, 55, 40), fill="gray")
    changed.save(second)

    assert perceptual_hash(first) != perceptual_hash(second)
    matches = find_near_duplicates([first, second], max_distance=6)

    assert len(matches) == 1
    assert matches[0][2] <= 6
