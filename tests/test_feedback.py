import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from vibesorter.feedback import (
    MAX_PREFERENCE_ADJUSTMENT,
    PersonalCorrectionStore,
    apply_personal_preferences,
)
from vibesorter.vibes import VibeScore


def _image(path: Path, color=(20, 80, 160)) -> Path:
    Image.new("RGB", (12, 12), color).save(path)
    return path


def test_correction_persists_and_is_deduplicated_by_content(tmp_path):
    image = _image(tmp_path / "one.png")
    duplicate = _image(tmp_path / "duplicate.png")
    db = tmp_path / "analysis.db"
    with PersonalCorrectionStore(db) as store:
        store.record(image, "retro", "correct")
        store.record(duplicate, "retro", "incorrect")
        assert len(store.list_corrections()) == 1
        assert store.list_corrections()[0]["path"] == str(duplicate.resolve())
    with PersonalCorrectionStore(db) as reopened:
        assert reopened.adjustments() == {"retro": -0.015}


def test_correction_undo_restores_previous_state_and_new_record(tmp_path):
    image = _image(tmp_path / "one.png")
    with PersonalCorrectionStore(tmp_path / "analysis.db") as store:
        store.record(image, "retro", "correct")
        store.record(image, "retro", "incorrect")
        assert store.adjustments() == {"retro": -0.015}
        assert store.undo_last()
        assert store.adjustments() == {"retro": 0.015}
        assert store.undo_last()
        assert store.adjustments() == {}
        assert not store.undo_last()


def test_partial_correction_updates_both_personal_preferences(tmp_path):
    image = _image(tmp_path / "one.png")
    with PersonalCorrectionStore(tmp_path / "analysis.db") as store:
        store.record(image, "retro", "partial", "dreamy")
        assert store.adjustments() == {"retro": -0.015, "dreamy": 0.015}


def test_preferences_are_bounded_and_do_not_mutate_raw_scores(tmp_path):
    with PersonalCorrectionStore(tmp_path / "analysis.db") as store:
        for index in range(10):
            sample = _image(tmp_path / f"sample-{index}.png", (index * 20, 80, 160))
            store.record(sample, "retro", "correct")
        assert store.adjustments()["retro"] == MAX_PREFERENCE_ADJUSTMENT
    raw = (VibeScore("retro", 0.60), VibeScore("dreamy", 0.61))
    personalized = apply_personal_preferences(raw, {"retro": 0.05})
    assert personalized[0].name == "retro"
    assert raw[0].score == 0.60


def test_clear_removes_records_and_undo_history(tmp_path):
    image = _image(tmp_path / "one.png")
    with PersonalCorrectionStore(tmp_path / "analysis.db") as store:
        store.record(image, "retro", "correct")
        assert store.clear() == 1
        assert store.list_corrections() == []
        assert not store.undo_last()


def test_partial_correction_rejects_same_label_and_unknown_vibe(tmp_path):
    image = _image(tmp_path / "one.png")
    with PersonalCorrectionStore(tmp_path / "analysis.db") as store:
        with pytest.raises(ValueError):
            store.record(image, "retro", "partial", "retro")
        with pytest.raises(ValueError):
            store.record(image, "not-a-vibe", "correct")


def test_changed_image_content_gets_a_separate_identity(tmp_path):
    image = _image(tmp_path / "one.png")
    with PersonalCorrectionStore(tmp_path / "analysis.db") as store:
        store.record(image, "retro", "correct")
        _image(image, (200, 20, 30))
        store.record(image, "dreamy", "correct")
        assert len(store.list_corrections()) == 2


def test_cli_can_inspect_undo_and_clear_corrections(tmp_path, monkeypatch, capsys):
    from vibesorter.entrypoint import main

    image = _image(tmp_path / "photo.png")
    db = tmp_path / "analysis.db"
    with PersonalCorrectionStore(db) as store:
        store.record(image, "retro", "correct")

    monkeypatch.setattr(sys, "argv", ["vibesorter", "corrections", "--db", str(db), "--json"])
    assert main() == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["local_only"] is True
    assert len(inspected["corrections"]) == 1

    monkeypatch.setattr(sys, "argv", ["vibesorter", "corrections", "--db", str(db), "--undo"])
    assert main() == 0
    assert "Undid" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["vibesorter", "corrections", "--db", str(db), "--clear"])
    assert main() == 0
    assert "Cleared 0" in capsys.readouterr().out
