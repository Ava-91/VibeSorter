from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from vibesorter.evaluation import (
    LabelledImage,
    evaluate_dataset,
    expected_calibration_error,
    load_labels,
)


def test_evaluation_report_includes_f1_and_ambiguity(tmp_path: Path) -> None:
    image = tmp_path / "red.png"
    Image.new("RGB", (20, 20), (230, 20, 20)).save(image)

    report = evaluate_dataset((LabelledImage(image, "Red / Warm"),))

    assert report.labelled_images == 1
    assert report.metrics.per_vibe["Red / Warm"]["f1"] == 1.0
    assert report.ambiguous == 0
    assert report.ambiguous_rate == 0.0
    assert report.confidence_error >= 0.0
    assert len(report.calibration) == 10


def test_zero_support_vibe_metrics_are_zero(tmp_path: Path) -> None:
    image = tmp_path / "red.png"
    Image.new("RGB", (20, 20), (230, 20, 20)).save(image)

    report = evaluate_dataset((LabelledImage(image, "Red / Warm"),))
    metrics = report.metrics.per_vibe["Soft / Pastel"]

    assert metrics["support"] == 0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0


def test_expected_calibration_error_is_zero_for_empty_data() -> None:
    assert expected_calibration_error(()) == 0.0


def test_jsonl_label_contract_remains_usable(tmp_path: Path) -> None:
    image = tmp_path / "fixture.png"
    Image.new("RGB", (16, 16), (80, 100, 140)).save(image)
    labels_file = tmp_path / "labels.jsonl"
    labels_file.write_text(
        json.dumps({"path": str(image), "label": "Soft / Pastel"}) + "\n",
        encoding="utf-8",
    )
    labels = load_labels(labels_file)
    assert len(labels) == 1
    assert labels[0].path == image
