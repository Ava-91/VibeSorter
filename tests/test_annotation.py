from pathlib import Path

import pytest

from vibesorter.annotation import ImageAnnotation, load_annotations, save_annotation
from vibesorter.profile import AttributeValue, ImageProfile


def profile() -> ImageProfile:
    return ImageProfile(
        media_type=AttributeValue("photograph", 1.0),
        colors=(AttributeValue("red", 1.0), AttributeValue("blue", 0.8)),
        temperature=AttributeValue("cool", 0.9),
        saturation=AttributeValue("muted", 0.9),
        brightness=AttributeValue("dark", 0.9),
        vibes=(AttributeValue("retro", 0.9), AttributeValue("moody", 0.8)),
    )


def test_annotation_round_trips_multiple_labels(tmp_path):
    output = tmp_path / "annotations.jsonl"
    annotation = ImageAnnotation(Path("a.jpg"), profile())
    save_annotation(output, annotation)
    loaded = load_annotations(output)
    assert loaded[str(Path("a.jpg").resolve())].profile == annotation.profile


def test_annotation_requires_attribute_values(tmp_path):
    output = tmp_path / "annotations.jsonl"
    invalid = ImageProfile()
    annotation = ImageAnnotation(tmp_path / "a.jpg", invalid)
    save_annotation(output, annotation)
    assert load_annotations(output)


def test_corrupt_annotation_is_reported(tmp_path):
    output = tmp_path / "annotations.jsonl"
    output.write_text('{"path": "a.jpg"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid annotation"):
        load_annotations(output)
