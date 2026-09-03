import json
import sqlite3
from pathlib import Path

import pytest

from vibesorter.browser.labeling_ui import render_label_page
from vibesorter.labeling import LabelCandidate, LabelSession, build_candidates, load_completed_labels, save_label
from vibesorter.vibes import VibeScore


def _candidate(path: Path, prediction: str = "Retro Blue", confidence: float = 0.43, ambiguous: bool = True) -> LabelCandidate:
    return LabelCandidate(path.resolve(), prediction, confidence, ambiguous, (VibeScore(prediction, 0.48), VibeScore("Soft / Pastel", 0.40)))


def test_build_candidates_prioritizes_ambiguous_then_confidence(tmp_path):
    root = tmp_path / "images"
    root.mkdir()
    paths = [root / f"image-{index}.jpg" for index in range(3)]
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE images(path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
        rows = [
            (str(paths[0]), 1, 1, "{}", json.dumps([{"name": "Retro Blue", "score": 0.70}, {"name": "Dark / Moody", "score": 0.20}])),
            (str(paths[1]), 1, 1, "{}", json.dumps([{"name": "Retro Blue", "score": 0.50}, {"name": "Soft / Pastel", "score": 0.49}])),
            (str(paths[2]), 1, 1, "{}", json.dumps([{"name": "Dark / Moody", "score": 0.60}, {"name": "Green & Black", "score": 0.59}])),
        ]
        conn.executemany("INSERT INTO images VALUES (?,?,?,?,?)", rows)
    candidates = build_candidates(db, root, count=3, uncertain_first=True)
    assert [item.path for item in candidates] == [paths[1].resolve(), paths[2].resolve(), paths[0].resolve()]


def test_label_session_persists_and_resumes(tmp_path):
    first = _candidate(tmp_path / "a.jpg")
    second = _candidate(tmp_path / "b.jpg", "Dark / Moody", 0.31)
    output = tmp_path / "labels.jsonl"
    session = LabelSession((first, second), output)
    session.decide(first, first.prediction)
    assert session.labelled == 1
    assert len(session.remaining) == 1
    assert load_completed_labels(output)[str(first.path)] == "Retro Blue"

    resumed = LabelSession((first, second), output)
    assert len(resumed.remaining) == 1
    resumed.decide(second, "Dark / Moody")
    records = output.read_text(encoding="utf-8").splitlines()
    assert len(records) == 2
    assert {json.loads(line)["label"] for line in records} == {"Retro Blue", "Dark / Moody"}


def test_save_label_rejects_unknown_vibe(tmp_path):
    candidate = _candidate(tmp_path / "a.jpg")
    with pytest.raises(ValueError, match="unknown vibe"):
        save_label(tmp_path / "labels.jsonl", candidate, "Not a vibe")


def test_label_page_contains_local_review_controls(tmp_path):
    session = LabelSession((_candidate(tmp_path / "a.jpg"),), tmp_path / "labels.jsonl")
    page = render_label_page(session)
    assert "Assisted labeling" in page
    assert "/api/label/decision" in page
    assert "Enter" in page and "1–7" in page and "Skip" in page and "Undo" in page
    assert str((tmp_path / "a.jpg").resolve()) in page
