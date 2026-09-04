import json
from pathlib import Path

from PIL import Image

from vibesorter.entrypoint import main


def test_train_command_writes_model(tmp_path, monkeypatch):
    image = Path(tmp_path) / "sample.png"
    Image.new("RGB", (8, 8), "navy").save(image)
    labels = Path(tmp_path) / "labels.jsonl"
    labels.write_text(
        json.dumps({"path": str(image), "label": "retro"}) + "\n", encoding="utf-8"
    )
    output = Path(tmp_path) / "model.json"
    monkeypatch.setattr(
        "sys.argv", ["vibesorter", "train", str(labels), "--output", str(output)]
    )
    assert main() == 0
    assert output.is_file()
