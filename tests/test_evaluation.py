from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.evaluation import LabelledImage, evaluate_labels, load_labels


def test_load_labels_reads_jsonl(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text('{"path":"red.png","label":"Red / Warm"}\n', encoding="utf-8")
    assert load_labels(labels) == (LabelledImage(Path("red.png"), "Red / Warm"),)


def test_evaluation_reports_accuracy_and_matrix(tmp_path: Path) -> None:
    image = tmp_path / "red.png"
    Image.new("RGB", (20, 20), (230, 20, 20)).save(image)
    metrics = evaluate_labels((LabelledImage(image, "Red / Warm"),))
    assert metrics.total == 1
    assert metrics.correct == 1
    assert metrics.accuracy == 1.0
    assert metrics.confusion_matrix["Red / Warm"]["Red / Warm"] == 1
