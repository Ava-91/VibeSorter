import json

from vibesorter.evaluation import evaluate_labels, load_labels


def test_jsonl_labels_can_be_loaded_and_evaluated(tmp_path):
    dataset = tmp_path / "labels.jsonl"
    dataset.write_text(json.dumps({"path": "missing.jpg", "label": "Soft / Pastel"}) + "\n")
    labels = load_labels(dataset)
    metrics = evaluate_labels(labels)
    assert metrics.total == 1
