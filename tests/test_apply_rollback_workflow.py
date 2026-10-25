"""End-to-end regressions for the documented propose -> review -> apply -> rollback workflow."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from vibesorter import entrypoint


def _run(monkeypatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["vibesorter", *argv])
    return entrypoint.main()


def _library(root: Path) -> Path:
    """Generated fixtures only; the name has a space and non-ASCII characters on purpose."""
    library = root / "ph otos"
    (library / "ñandú").mkdir(parents=True)
    Image.new("RGB", (64, 48), (30, 120, 220)).save(library / "blue.png")
    Image.new("RGB", (64, 48), (128, 128, 128)).save(library / "gray.png")
    Image.new("RGB", (40, 40), (5, 5, 5)).save(library / "ñandú" / "café.jpg")
    return library


def _snapshot(library: Path) -> dict[str, bytes]:
    return {
        path.relative_to(library).as_posix(): path.read_bytes()
        for path in sorted(library.rglob("*"))
        if path.is_file() and ".vibesorter" not in path.parts
    }


def _write_reviewed(monkeypatch, work: Path, library: Path) -> tuple[Path, dict]:
    proposal, reviewed = work / "proposal.json", work / "reviewed.json"
    assert _run(monkeypatch, "propose", str(library), "--output-root", str(work / "Sorted"),
                "--output", str(proposal)) == 0
    assert _run(monkeypatch, "review", str(proposal), "--accept", "all", "--output", str(reviewed)) == 0
    return reviewed, json.loads(reviewed.read_text(encoding="utf-8"))


def test_reviewed_proposal_keeps_safety_roots_and_absolute_sources(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    library = _library(tmp_path)
    monkeypatch.chdir(tmp_path)  # relative library path, like a real user would type

    _, data = _write_reviewed(monkeypatch, work, Path("ph otos"))

    assert data["source_root"] == str(library.resolve())
    assert all(Path(operation["source"]).is_absolute() for operation in data["operations"])


def test_apply_and_rollback_work_from_any_working_directory(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    library = _library(tmp_path)
    original = _snapshot(library)
    monkeypatch.chdir(tmp_path)
    reviewed, _ = _write_reviewed(monkeypatch, work, Path("ph otos"))
    history = work / "history.jsonl"

    assert _run(monkeypatch, "apply", str(reviewed), "--dry-run", "--history", str(history)) == 0
    assert _snapshot(library) == original

    capsys.readouterr()
    assert _run(monkeypatch, "apply", str(reviewed), "--confirm", "--history", str(history)) == 0
    output = capsys.readouterr().out
    assert _snapshot(library) != original, "at least one image should have been moved"
    batch_id = next(line.split()[-1] for line in output.splitlines() if line.startswith("Batch ID:"))

    monkeypatch.chdir(elsewhere)  # rollback must not depend on where it is run from
    assert _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history)) == 0

    assert _snapshot(library) == original
    assert list(elsewhere.iterdir()) == []


def test_refused_apply_exits_nonzero_and_reports_no_batch(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    library = _library(tmp_path)
    original = _snapshot(library)
    monkeypatch.chdir(tmp_path)
    reviewed, data = _write_reviewed(monkeypatch, work, Path("ph otos"))
    del data["source_root"]  # a proposal without its safety boundary must be refused
    reviewed.write_text(json.dumps(data), encoding="utf-8")

    capsys.readouterr()
    code = _run(monkeypatch, "apply", str(reviewed), "--confirm", "--history", str(work / "history.jsonl"))
    output = capsys.readouterr().out

    assert code != 0
    assert "Batch ID" not in output
    assert "No filesystem changes were made." in output
    assert _snapshot(library) == original


def _apply_batch(monkeypatch, capsys, tmp_path):
    """Apply a reviewed proposal on generated fixtures; return (library, original, history, batch_id, moved paths)."""
    work = tmp_path / "work"
    work.mkdir()
    library = _library(tmp_path)
    original = _snapshot(library)
    monkeypatch.chdir(tmp_path)
    reviewed, data = _write_reviewed(monkeypatch, work, Path("ph otos"))
    history = work / "history.jsonl"
    capsys.readouterr()
    assert _run(monkeypatch, "apply", str(reviewed), "--confirm", "--history", str(history)) == 0
    batch_id = next(
        line.split()[-1] for line in capsys.readouterr().out.splitlines() if line.startswith("Batch ID:")
    )
    records = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines()]
    return library, original, history, batch_id, records


def test_repeated_rollback_is_idempotent_and_says_so(tmp_path, monkeypatch, capsys):
    library, original, history, batch_id, records = _apply_batch(monkeypatch, capsys, tmp_path)
    assert len(records) >= 2

    assert _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history)) == 0
    assert f"Restored {len(records)} of {len(records)}" in capsys.readouterr().out
    assert _snapshot(library) == original

    # Nothing is left to restore, and nothing is wrong: succeed, but say what happened.
    assert _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history)) == 0
    output = capsys.readouterr().out
    assert f"Restored 0 of {len(records)}" in output
    assert f"{len(records)} already back" in output
    assert _snapshot(library) == original


def test_partial_rollback_restores_what_is_safe_and_reports_the_rest(tmp_path, monkeypatch, capsys):
    library, original, history, batch_id, records = _apply_batch(monkeypatch, capsys, tmp_path)
    missing, modified, occupied = records[0], records[1], records[2] if len(records) > 2 else None
    Path(missing["destination"]).unlink()  # user deleted a moved file
    Path(modified["destination"]).write_bytes(b"edited after the move")  # content changed
    if occupied is not None:
        Path(occupied["source"]).write_bytes(b"someone else's file")  # original path reused
    untouched_edit = Path(modified["destination"]).read_bytes()

    code = _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history))
    output = capsys.readouterr().out

    assert code == 1
    assert "missing" in output and "conflict" in output
    assert Path(modified["destination"]).read_bytes() == untouched_edit  # never overwritten or moved
    assert not Path(modified["source"]).exists()
    if occupied is not None:
        assert Path(occupied["source"]).read_bytes() == b"someone else's file"
    restored = len(records) - (3 if occupied is not None else 2)
    assert f"Restored {restored} of {len(records)}" in output


def test_rollback_filesystem_error_is_reported_without_losing_the_file(tmp_path, monkeypatch, capsys):
    from vibesorter import history as history_module

    library, original, history, batch_id, records = _apply_batch(monkeypatch, capsys, tmp_path)

    def denied(src, dst, *args, **kwargs):
        raise PermissionError("simulated permission denied")

    monkeypatch.setattr(history_module.shutil, "move", denied)
    code = _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history))
    output = capsys.readouterr().out

    assert code == 1
    assert "simulated permission denied" in output
    assert "Restored 0 of" in output
    assert all(Path(record["destination"]).is_file() for record in records)  # nothing lost


def test_rollback_dry_run_never_changes_files(tmp_path, monkeypatch, capsys):
    library, original, history, batch_id, records = _apply_batch(monkeypatch, capsys, tmp_path)
    moved_state = {record["destination"]: Path(record["destination"]).read_bytes() for record in records}

    assert _run(monkeypatch, "rollback", batch_id, "--dry-run", "--history", str(history)) == 0
    assert "Can restore" in capsys.readouterr().out
    assert {path: Path(path).read_bytes() for path in moved_state} == moved_state
    assert not any(Path(record["source"]).exists() for record in records)


def test_rollback_of_unknown_batch_fails_cleanly(tmp_path, monkeypatch, capsys):
    library, original, history, batch_id, records = _apply_batch(monkeypatch, capsys, tmp_path)
    try:
        _run(monkeypatch, "rollback", "no-such-batch", "--confirm", "--history", str(history))
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("an unknown batch must exit with an error")
