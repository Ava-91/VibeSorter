from __future__ import annotations

import json
import sys
from pathlib import Path

import vibesorter.entrypoint as entrypoint
from vibesorter.benchmark import BenchmarkResult
from vibesorter.explain import Explanation


def test_benchmark_command_json(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        entrypoint,
        "benchmark",
        lambda folder, recursive, repeats: BenchmarkResult(3, repeats, 1.5, 2.0, 500.0),
    )
    monkeypatch.setattr(sys, "argv", ["vibesorter", "benchmark", str(tmp_path), "--repeats", "2", "--json"])

    assert entrypoint.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["images"] == 3
    assert data["repeats"] == 2
    assert data["milliseconds_per_image"] == 500.0


def test_benchmark_rejects_zero_repeats(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["vibesorter", "benchmark", str(tmp_path), "--repeats", "0"])
    try:
        entrypoint.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse validation failure")


def test_explain_command_json(monkeypatch, capsys, tmp_path):
    image = tmp_path / "image.jpg"
    monkeypatch.setattr(
        entrypoint,
        "explain_image",
        lambda path: Explanation(Path(path), "Retro Blue", 0.8, 0.2, False, (("Retro Blue", 0.8), ("Dark / Moody", 0.6)), {"brightness": 0.4}),
    )
    monkeypatch.setattr(sys, "argv", ["vibesorter", "explain", str(image), "--json"])

    assert entrypoint.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["winner"] == "Retro Blue"
    assert data["scores"][0][0] == "Retro Blue"


def test_explain_command_human_output(monkeypatch, capsys, tmp_path):
    image = tmp_path / "image.jpg"
    monkeypatch.setattr(
        entrypoint,
        "explain_image",
        lambda path: Explanation(Path(path), "Dark / Moody", 0.75, 0.1, True, (("Dark / Moody", 0.75),), {"contrast": 0.7}),
    )
    monkeypatch.setattr(sys, "argv", ["vibesorter", "explain", str(image)])

    assert entrypoint.main() == 0
    output = capsys.readouterr().out
    assert "Winner: Dark / Moody" in output
    assert "Ambiguous: yes" in output


def test_index_command_parses_folder_and_options(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(
        entrypoint,
        "index_folder",
        lambda folder, recursive, workers: {
            "total": 2,
            "analyzed": 1,
            "reused": 1,
            "skipped": 0,
            "removed": 0,
            "database": str(tmp_path / ".vibesorter" / "analysis.db"),
        },
    )
    monkeypatch.setattr(sys, "argv", ["vibesorter", "index", str(tmp_path), "--no-recursive", "--workers", "3", "--json"])

    assert entrypoint.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["total"] == 2
    assert data["analyzed"] == 1
    assert data["reused"] == 1
