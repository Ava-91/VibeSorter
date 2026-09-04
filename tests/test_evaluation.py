from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.evaluation import LabelledImage, evaluate_labels, load_labels


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
    assert "retro" in metrics.confusion_matrix
    assert "Retro Blue" not in metrics.confusion_matrix
