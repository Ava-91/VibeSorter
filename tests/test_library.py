from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.library import analyze_library


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
