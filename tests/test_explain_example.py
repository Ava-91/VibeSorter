import json
from pathlib import Path


def test_explain_example_has_core_fields():
    path = Path(__file__).parents[1] / "docs" / "explain-output.example.json"
    data = json.loads(path.read_text())
    assert {
        "path",
        "winner",
        "confidence",
        "margin",
        "ambiguous",
        "scores",
        "feature_signals",
        "score_contributions",
        "features",
    } <= data.keys()
    assert data["features"]["path"] == data["path"]
