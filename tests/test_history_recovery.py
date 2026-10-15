from __future__ import annotations

import errno
from pathlib import Path

import pytest

import vibesorter.history as history
from vibesorter.history import load_batch, record_batch, rollback_batch
from vibesorter.operations import MoveResult


def _seed_batch(tmp_path: Path, count: int = 1) -> tuple[Path, list[Path], list[Path]]:
    history_path = tmp_path / ".vibesorter" / "history.jsonl"
    sources = [tmp_path / "originals" / f"photo-{index}.jpg" for index in range(count)]
    destinations = [tmp_path / "sorted" / f"photo-{index}.jpg" for index in range(count)]
    results = []
    for index, destination in enumerate(destinations, start=1):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"image-{index}".encode())
        results.append(MoveResult(index, "moved", sources[index - 1], destination))
    record_batch("recovery-batch", tuple(results), history_path)
    return history_path, sources, destinations


def test_rollback_refuses_modified_or_deleted_destinations(tmp_path: Path) -> None:
    history_path, sources, destinations = _seed_batch(tmp_path, count=2)
    destinations[0].write_bytes(b"modified")
    destinations[1].unlink()

    results = rollback_batch(history_path, "recovery-batch", confirm=True)

    by_id = {result["operation_id"]: result for result in results}
    assert by_id[1]["status"] == "conflict"
    assert by_id[2]["status"] == "missing"
    assert destinations[0].read_bytes() == b"modified"
    assert not sources[0].exists() and not sources[1].exists()


def test_rollback_refuses_to_overwrite_occupied_source(tmp_path: Path) -> None:
    history_path, sources, destinations = _seed_batch(tmp_path)
    sources[0].parent.mkdir(parents=True)
    sources[0].write_bytes(b"unrelated data")

    result = rollback_batch(history_path, "recovery-batch", confirm=True)[0]

    assert result["status"] == "conflict"
    assert result["detail"] == "original source path is occupied"
    assert sources[0].read_bytes() == b"unrelated data"
    assert destinations[0].is_file()


def test_corrupt_history_reports_line_number(tmp_path: Path) -> None:
    history_path, _, _ = _seed_batch(tmp_path)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write("{this is not json}\n")

    with pytest.raises(ValueError, match="corrupt history at line 2"):
        load_batch(history_path, "recovery-batch")


def test_rollback_permission_error_is_reported_and_preserves_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    history_path, sources, destinations = _seed_batch(tmp_path)

    def deny_move(_source, _destination):
        raise PermissionError("restore denied")

    monkeypatch.setattr(history.shutil, "move", deny_move)
    result = rollback_batch(history_path, "recovery-batch", confirm=True)[0]

    assert result["status"] == "error"
    assert "restore denied" in result["detail"]
    assert destinations[0].is_file()
    assert not sources[0].exists()


def test_rollback_uses_copy_fallback_for_cross_device_move(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    history_path, sources, destinations = _seed_batch(tmp_path)
    def cross_device_once(source, destination):
        raise OSError(errno.EXDEV, "simulated cross-device move")

    monkeypatch.setattr(history.os, "rename", cross_device_once)
    result = rollback_batch(history_path, "recovery-batch", confirm=True)[0]

    assert result["status"] == "restored"
    assert sources[0].read_bytes() == b"image-1"
    assert not destinations[0].exists()


def test_partial_rollback_continues_and_reports_failed_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    history_path, sources, destinations = _seed_batch(tmp_path, count=2)
    real_move = history.shutil.move

    def fail_second_restore(source, destination):
        if Path(source) == destinations[1]:
            raise OSError("simulated restore failure")
        return real_move(source, destination)

    monkeypatch.setattr(history.shutil, "move", fail_second_restore)
    results = rollback_batch(history_path, "recovery-batch", confirm=True)

    by_id = {result["operation_id"]: result for result in results}
    assert by_id[2]["status"] == "error"
    assert "simulated restore failure" in by_id[2]["detail"]
    assert by_id[1]["status"] == "restored"
    assert sources[0].read_bytes() == b"image-1"
    assert destinations[1].read_bytes() == b"image-2"
    assert not sources[1].exists()


def test_disk_full_during_history_fsync_restores_moved_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "original.jpg"
    destination = tmp_path / "sorted" / "original.jpg"
    destination.parent.mkdir()
    destination.write_bytes(b"image")
    history_path = tmp_path / ".vibesorter" / "history.jsonl"
    history_path.parent.mkdir()
    history_path.write_text('{"event":"prior"}\n', encoding="utf-8")

    def disk_full(_fd: int) -> None:
        raise OSError("No space left on device")

    monkeypatch.setattr(history.os, "fsync", disk_full)
    with pytest.raises(OSError, match="No space left on device"):
        record_batch("disk-full-batch", (MoveResult(1, "moved", source, destination),), history_path)

    assert source.read_bytes() == b"image"
    assert not destination.exists()
    assert history_path.read_text(encoding="utf-8") == '{"event":"prior"}\n'


def test_atomic_history_failure_preserves_previous_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "original.jpg"
    destination = tmp_path / "sorted" / "original.jpg"
    destination.parent.mkdir()
    destination.write_bytes(b"image")
    history_path = tmp_path / ".vibesorter" / "history.jsonl"
    history_path.parent.mkdir()
    history_path.write_text('{"event":"prior"}\n', encoding="utf-8")

    def fail_replace(_source: str, _destination: Path) -> None:
        raise OSError("simulated atomic replace failure")

    monkeypatch.setattr(history.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated atomic replace failure"):
        record_batch("replace-fail-batch", (MoveResult(1, "moved", source, destination),), history_path)

    assert source.read_bytes() == b"image"
    assert not destination.exists()
    assert history_path.read_text(encoding="utf-8") == '{"event":"prior"}\n'
