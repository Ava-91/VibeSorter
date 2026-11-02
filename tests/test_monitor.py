from __future__ import annotations

from pathlib import Path

import pytest

from vibesorter import monitor


def test_snapshot_includes_images_but_excludes_managed_directory(tmp_path: Path) -> None:
    image = tmp_path / "cover.jpg"
    image.write_bytes(b"image")
    managed = tmp_path / ".vibesorter"
    managed.mkdir()
    (managed / "internal.jpg").write_bytes(b"internal")

    snapshot = monitor._snapshot(tmp_path)

    assert [Path(item[0]).name for item in snapshot] == ["cover.jpg"]


def test_monitor_reindexes_when_snapshot_changes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    snapshots = iter([(("cover.jpg", 10, 1),), (("cover.jpg", 12, 2),)])
    calls: list[dict[str, int | str]] = []

    monkeypatch.setattr(monitor, "_snapshot", lambda _folder: next(snapshots))

    def fake_index(_folder: str | Path, *, workers: int) -> dict[str, int | str]:
        result = {"total": len(calls) + 1, "analyzed": 1, "reused": 0, "skipped": 0, "removed": 0, "database": "cache.db"}
        return result

    monkeypatch.setattr(monitor, "index_folder", fake_index)

    class StopAfterOnePoll:
        waits = 0

        def is_set(self) -> bool:
            return False

        def wait(self, _interval: float) -> bool:
            self.waits += 1
            return self.waits > 1

    updates: list[dict[str, int | str]] = []
    result = monitor.monitor_folder(
        tmp_path,
        interval=5,
        on_update=updates.append,
        stop_event=StopAfterOnePoll(),  # type: ignore[arg-type]
    )

    assert len(updates) == 2
    assert result["total"] == 2


def test_monitor_rejects_too_frequent_polling(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 5 seconds"):
        monitor.monitor_folder(tmp_path, interval=1)
