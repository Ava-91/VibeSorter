import json

from PIL import Image

from vibesorter.evaluation import evaluate_labels, load_labels


def test_jsonl_labels_can_be_loaded_and_evaluated(tmp_path):
    image = tmp_path / "fixture.png"
    Image.new("RGB", (16, 16), (80, 100, 140)).save(image)

    dataset = tmp_path / "labels.jsonl"
    dataset.write_text(
        json.dumps({"path": str(image), "label": "Soft / Pastel"}) + "\n"
    )
    labels = load_labels(dataset)
    metrics = evaluate_labels(labels)
    assert metrics.total == 1
