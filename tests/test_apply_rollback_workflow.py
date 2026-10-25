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


def test_repeated_rollback_reports_failure_instead_of_success(tmp_path, monkeypatch, capsys):
    work = tmp_path / "work"
    work.mkdir()
    library = _library(tmp_path)
    original = _snapshot(library)
    monkeypatch.chdir(tmp_path)
    reviewed, _ = _write_reviewed(monkeypatch, work, Path("ph otos"))
    history = work / "history.jsonl"
    capsys.readouterr()
    assert _run(monkeypatch, "apply", str(reviewed), "--confirm", "--history", str(history)) == 0
    batch_id = next(
        line.split()[-1] for line in capsys.readouterr().out.splitlines() if line.startswith("Batch ID:")
    )

    assert _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history)) == 0
    assert "Restored" in capsys.readouterr().out
    assert _snapshot(library) == original

    # Nothing is left to restore: the CLI must say so and exit non-zero.
    assert _run(monkeypatch, "rollback", batch_id, "--confirm", "--history", str(history)) == 1
    output = capsys.readouterr().out
    assert "Restored 0 of" in output
    assert "missing" in output
    assert _snapshot(library) == original
