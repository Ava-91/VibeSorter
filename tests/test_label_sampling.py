from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from vibesorter.label_sampling import (
    sample_image_paths,
    sample_labels,
    write_label_template,
)


def _make_images(folder: Path, count: int) -> list[Path]:
    paths = []
    for index in range(count):
        path = folder / f"image-{index:03d}.png"
        Image.new("RGB", (2, 2), (index % 255, 20, 40)).save(path)
        paths.append(path)
    return paths


def test_sample_image_paths_is_deterministic_and_evenly_distributed(tmp_path):
    images = _make_images(tmp_path, 10)
    first = sample_image_paths(images, 4)
    second = sample_image_paths(images, 4)

    assert first == second
    assert first == [images[0], images[3], images[6], images[9]]


def test_sample_image_paths_rejects_invalid_counts(tmp_path):
    images = _make_images(tmp_path, 3)

    with pytest.raises(ValueError, match="at least 1"):
        sample_image_paths(images, 0)
    with pytest.raises(ValueError, match="exceeds available images"):
        sample_image_paths(images, 4)


def test_write_label_template_contains_absolute_paths_and_blank_labels(tmp_path):
    images = _make_images(tmp_path, 2)
    output = tmp_path / "labels.jsonl"

    result = write_label_template(images, output)
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert result == output
    assert records == [{"path": str(path.resolve()), "label": ""} for path in images]


def test_sample_labels_discovers_recursive_images_and_writes_template(tmp_path):
    root = tmp_path / "library"
    nested = root / "nested"
    nested.mkdir(parents=True)
    _make_images(root, 2)
    _make_images(nested, 2)
    output = tmp_path / "labels.jsonl"

    result = sample_labels(root, count=3, output=output)
    records = output.read_text(encoding="utf-8").splitlines()

    assert result == {"available": 4, "selected": 3, "output": str(output)}
    assert len(records) == 3


def test_sample_labels_rejects_missing_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        sample_labels(tmp_path / "missing", count=1, output=tmp_path / "labels.jsonl")
