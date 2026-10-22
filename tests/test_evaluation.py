from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.evaluation import (
    CANONICAL_VIBES,
    LabelledImage,
    evaluate_dataset,
    evaluate_labels,
    load_labels,
)


def test_load_labels_reads_jsonl(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text('{"path":"red.png","label":"retro"}\n', encoding="utf-8")
    assert load_labels(labels) == (LabelledImage(Path("red.png"), "retro"),)


def test_evaluation_reports_accuracy_and_canonical_matrix(tmp_path: Path) -> None:
    image = tmp_path / "red.png"
    Image.new("RGB", (20, 20), (230, 20, 20)).save(image)
    metrics = evaluate_labels((LabelledImage(image, "retro"),))
    assert metrics.total == 1
    assert metrics.accuracy in {0.0, 1.0}
    assert set(metrics.confusion_matrix) == set(CANONICAL_VIBES)
    assert metrics.per_vibe["retro"]["support"] == 1
    assert "Retro Blue" not in metrics.confusion_matrix


def test_evaluation_rejects_noncanonical_legacy_compound_label(tmp_path: Path) -> None:
    import pytest
    labels = tmp_path / "legacy-labels.jsonl"
    labels.write_text('{"path":"red.png","label":"Retro Blue"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown vibe label"):
        load_labels(labels)


def test_dataset_report_contains_canonical_support_and_calibration(tmp_path: Path) -> None:
    first, second = tmp_path / "first.png", tmp_path / "second.png"
    Image.new("RGB", (20, 20), (230, 20, 20)).save(first)
    Image.new("RGB", (20, 20), (20, 30, 70)).save(second)
    labels = (LabelledImage(first, "romantic"), LabelledImage(second, "moody"))
    report = evaluate_dataset(labels, bins=4)
    assert report.labelled_images == 2
    assert set(report.metrics.per_vibe) == set(CANONICAL_VIBES)
    assert sum(item["support"] for item in report.metrics.per_vibe.values()) == 2
    assert len(report.calibration) == 4
    assert 0.0 <= report.confidence_error <= 1.0
    assert 0 <= report.ambiguous <= 2
