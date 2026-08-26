import json
from pathlib import Path


def test_label_example_uses_jsonl_and_known_vibes():
    path = Path(__file__).parents[1] / "docs" / "label-schema.jsonl.example"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert all({"path", "vibe"} <= row.keys() for row in rows)
