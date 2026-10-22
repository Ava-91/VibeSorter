from pathlib import Path

from PIL import Image

from vibesorter.evaluation import (
    CANONICAL_VIBES,
    MultiLabelledImage,
    evaluate_multilabel_labels,
    load_multilabel_labels,
)


def test_load_multilabel_labels_validates_canonical_labels(tmp_path: Path) -> None:
    labels = tmp_path / "multi.jsonl"
    labels.write_text(
        '{"path":"sample.png","labels":["dreamy","soft"]}\n',
        encoding="utf-8",
    )
    assert load_multilabel_labels(labels) == (
        MultiLabelledImage(Path("sample.png"), ("dreamy", "soft")),
    )


def test_multilabel_evaluation_reports_per_vibe_metrics(tmp_path: Path) -> None:
    image = tmp_path / "sample.png"
    Image.new("RGB", (20, 20), (220, 200, 180)).save(image)
    report = evaluate_multilabel_labels((MultiLabelledImage(image, ("dreamy", "soft")),))
    assert report.total == 1
    assert 0.0 <= report.exact_match <= 1.0
    assert 0.0 <= report.micro_f1 <= 1.0
    assert set(report.per_vibe) == set(CANONICAL_VIBES)
    assert sum(item["support"] for item in report.per_vibe.values()) == 2


def test_multilabel_loader_rejects_empty_unknown_or_duplicate_labels(tmp_path: Path) -> None:
    import pytest

    labels = tmp_path / "invalid.jsonl"
    for record in (
        '{"path":"sample.png","labels":[]}',
        '{"path":"sample.png","labels":["not-a-vibe"]}',
        '{"path":"sample.png","labels":["soft","soft"]}',
    ):
        labels.write_text(record + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_multilabel_labels(labels)
