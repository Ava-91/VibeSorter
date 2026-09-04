from __future__ import annotations

from pathlib import Path

from vibesorter import cli
from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.pipeline import AnalysisResult
from vibesorter.search import ImageQuery, search_cache
from vibesorter.vibes import VibeScore


def _sample_result(path: Path) -> AnalysisResult:
    features = ImageFeatures(
        path,
        (10, 20, 30),
        (0.5, 0.6, 0.7),
        0.7,
        0.6,
        0.3,
        0.1,
        0.8,
        0.05,
        0.2,
        0.4,
        0.1,
        (ColorSample((8, 18, 28), 1.0),),
    )
    scores = (VibeScore("minimal", 0.82), VibeScore("cozy", 0.41))
    return AnalysisResult(path, features, scores[0], scores)


def test_legacy_folder_analysis_populates_search_cache(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"image")
    result = _sample_result(image)
    monkeypatch.setattr(cli, "_analyze_many", lambda images, workers: iter(((result, None),)))

    cache_path = tmp_path / ".vibesorter" / "analysis.db"
    cache = AnalysisCache(cache_path)
    try:
        groups, results, skipped = cli._analyze_folder(
            [image],
            1,
            min_score=0.9,
            show_progress=False,
            cache=cache,
        )
    finally:
        cache.close()

    assert groups == {}
    assert results == []
    assert skipped == 0

    with AnalysisCache(cache_path) as restored_cache:
        matches = search_cache(restored_cache, ImageQuery(vibe="minimal"))

    assert len(matches) == 1
    assert matches[0].path == image
    assert matches[0].best.name == "minimal"
