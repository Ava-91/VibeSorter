from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.library import analyze_library, analyze_library_stats


def test_analyze_library_persists_and_reuses_results(tmp_path: Path) -> None:
    image = tmp_path / "blue.png"
    Image.new("RGB", (16, 16), (20, 60, 180)).save(image)

    first = list(analyze_library(tmp_path))
    second = list(analyze_library(tmp_path))

    assert len(first) == len(second) == 1
    assert first[0].cached is False
    assert second[0].cached is True
    assert second[0].scores == first[0].scores
    assert (tmp_path / ".vibesorter" / "analysis.json").exists()


def test_library_stats_distinguish_fresh_and_cached_work(tmp_path: Path) -> None:
    Image.new("RGB", (16, 16), (220, 30, 20)).save(tmp_path / "red.png")
    first = analyze_library_stats(tmp_path)
    second = analyze_library_stats(tmp_path)
    assert first.total == 1
    assert first.analyzed == 1
    assert first.cached == 0
    assert second.total == 1
    assert second.analyzed == 0
    assert second.cached == 1
