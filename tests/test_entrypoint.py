from __future__ import annotations

import json
import sys
from pathlib import Path

from vibesorter import entrypoint
from vibesorter.benchmark import BenchmarkResult
from vibesorter.evaluation import ClassificationMetrics, EvaluationReport
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


def test_evaluate_command_json(monkeypatch, capsys, tmp_path):
    labels = tmp_path / "labels.jsonl"
    labels.write_text("{}\n", encoding="utf-8")
    metrics = ClassificationMetrics(
        total=4,
        correct=3,
        accuracy=0.75,
        per_vibe={"Red / Warm": {"support": 2, "precision": 0.8, "recall": 1.0, "f1": 0.8889}},
        confusion_matrix={"Red / Warm": {"Red / Warm": 2}},
    )
    report = EvaluationReport(metrics, 4, 1, 0.25, 0.1, [])
    monkeypatch.setattr(entrypoint, "evaluate_dataset", lambda loaded, bins: report)
    monkeypatch.setattr(sys, "argv", ["vibesorter", "evaluate", str(labels), "--bins", "5", "--json"])
    monkeypatch.setattr(entrypoint, "load_labels", lambda path: ())

    assert entrypoint.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["metrics"]["accuracy"] == 0.75
    assert data["metrics"]["per_vibe"]["Red / Warm"]["f1"] == 0.8889
    assert data["ambiguous_rate"] == 0.25


def test_evaluate_rejects_zero_bins(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["vibesorter", "evaluate", str(tmp_path / "labels.jsonl"), "--bins", "0"])
    try:
        entrypoint.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse validation failure")


def test_explain_command_json(monkeypatch, capsys, tmp_path):
    image = tmp_path / "image.jpg"
    explanation = Explanation(
        Path(image),
        "Retro Blue",
        0.8,
        0.2,
        False,
        (("Retro Blue", 0.8), ("Dark / Moody", 0.6)),
        (("Retro Blue", 0.8), ("Dark / Moody", 0.6)),
        {"brightness": 0.4},
        {"Retro Blue": {"brightness": 0.8}, "Dark / Moody": {"brightness": 0.6}},
        {"path": Path(image), "brightness": 0.4},
    )
    monkeypatch.setattr(entrypoint, "explain_image", lambda path: explanation)
    monkeypatch.setattr(sys, "argv", ["vibesorter", "explain", str(image), "--json"])

    assert entrypoint.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["winner"] == "Retro Blue"
    assert data["scores"][0][0] == "Retro Blue"
    assert data["score_contributions"]["Retro Blue"]["brightness"] == 0.8
    assert data["features"]["path"] == str(image)


def test_explain_command_human_output(monkeypatch, capsys, tmp_path):
    image = tmp_path / "image.jpg"
    explanation = Explanation(
        Path(image),
        "Dark / Moody",
        0.75,
        0.1,
        True,
        (("Dark / Moody", 0.75),),
        (("Dark / Moody", 0.75),),
        {"contrast": 0.7},
        {"Dark / Moody": {"contrast": 0.161}},
        {"path": Path(image), "contrast": 0.7},
    )
    monkeypatch.setattr(entrypoint, "explain_image", lambda path: explanation)
    monkeypatch.setattr(sys, "argv", ["vibesorter", "explain", str(image)])

    assert entrypoint.main() == 0
    output = capsys.readouterr().out
    assert "Winner: Dark / Moody" in output
    assert "Ambiguous: yes" in output
    assert "Score contributions:" in output
    assert "contrast" in output


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


def test_sample_labels_command(monkeypatch, capsys, tmp_path):
    output = tmp_path / "labels.jsonl"
    monkeypatch.setattr(
        entrypoint,
        "sample_labels",
        lambda folder, count, output, recursive: {
            "available": 1303,
            "selected": count,
            "output": str(output),
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["vibesorter", "sample-labels", str(tmp_path), "--count", "150", "--output", str(output), "--no-recursive"],
    )

    assert entrypoint.main() == 0
    text = capsys.readouterr().out
    assert "Sampled 150 image(s) from 1303" in text
    assert f"Label template: {output}" in text


def test_sample_labels_rejects_zero_count(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["vibesorter", "sample-labels", str(tmp_path), "--count", "0"])
    try:
        entrypoint.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected argparse validation failure")
