from __future__ import annotations

from pathlib import Path

import pytest

from vibesorter.history import list_history, load_batch, record_batch, rollback_batch
from vibesorter.operations import MoveResult


def _moved(source: Path, destination: Path) -> MoveResult:
    return MoveResult(1, "moved", source, destination)


def test_record_batch_writes_batch_and_rolls_back(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "Sorted" / "source.jpg"
    source.write_bytes(b"image")
    destination.parent.mkdir()
    source.replace(destination)

    history = tmp_path / ".vibesorter" / "history.jsonl"
    results = (_moved(source, destination),)
    count = record_batch("batch-1", results, history)

    assert count == 1
    assert history.is_file()
    assert load_batch(history, "batch-1")[0].sha256
    assert list_history(history)[0]["batch_id"] == "batch-1"

    rollback = rollback_batch(history, "batch-1", confirm=True)
    assert rollback[0]["status"] == "restored"
    assert source.is_file()
    assert not destination.exists()


def test_record_batch_failure_restores_moves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "Sorted" / "source.jpg"
    source.write_bytes(b"image")
    destination.parent.mkdir()
    source.replace(destination)
    history = tmp_path / ".vibesorter" / "history.jsonl"

    def fail_replace(_src: str, _dst: Path) -> None:
        raise OSError("simulated history failure")

    monkeypatch.setattr("vibesorter.history.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated history failure"):
        record_batch("batch-2", (_moved(source, destination),), history)

    assert source.is_file()
    assert not destination.exists()
    assert not history.exists()


def test_record_batch_ignores_non_moved_results(tmp_path: Path) -> None:
    source = tmp_path / "missing.jpg"
    destination = tmp_path / "Sorted" / "missing.jpg"
    history = tmp_path / ".vibesorter" / "history.jsonl"

    result = MoveResult(1, "missing", source, destination)
    assert record_batch("batch-3", (result,), history) == 0
    assert not history.exists()
