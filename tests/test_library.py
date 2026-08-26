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


def test_library_stats_distinguish_fresh_and_cached_work(tmp_path: Path) -> None:
    Image.new("RGB", (16, 16), (220, 30, 20)).save(tmp_path / "red.png")
    first = analyze_library_stats(tmp_path)
    second = analyze_library_stats(tmp_path)
    assert first.analyzed == 1 and first.cached == 0
    assert second.analyzed == 0 and second.cached == 1


def test_changed_library_image_is_reanalyzed(tmp_path: Path) -> None:
    image = tmp_path / "photo.png"
    Image.new("RGB", (16, 16), (220, 30, 20)).save(image)
    first = list(analyze_library(tmp_path))
    Image.new("RGB", (16, 16), (20, 60, 180)).save(image)
    second = list(analyze_library(tmp_path))
    assert first[0].cached is False
    assert second[0].cached is False
    assert second[0].best.name != first[0].best.name or second[0].scores != first[0].scores
