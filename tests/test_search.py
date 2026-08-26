from __future__ import annotations

from pathlib import Path

from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.pipeline import AnalysisResult
from vibesorter.search import ImageQuery, search_cache
from vibesorter.vibes import VibeScore


def result(path: Path, *, vibe: str = "Retro Blue", score: float = 0.82, brightness: float = 0.6, saturation: float = 0.7, contrast: float = 0.3, text: float = 0.1) -> AnalysisResult:
    features = ImageFeatures(path, (20, 40, 80), (0.6, saturation, brightness), brightness, saturation, contrast, 0.1, 0.7, 0.05, 0.2, 0.3, text, (ColorSample((20, 40, 80), 1.0),))
    scores = (VibeScore(vibe, score), VibeScore("Dark / Moody", 0.2))
    return AnalysisResult(path, features, scores[0], scores, cached=True)


def seed(cache: AnalysisCache, *results: AnalysisResult) -> None:
    for item in results:
        cache.set(item.path, item.features, item.scores)


def test_search_filters_by_vibe_and_score(tmp_path: Path) -> None:
    blue = tmp_path / "blue.jpg"
    dark = tmp_path / "dark.jpg"
    blue.write_bytes(b"blue")
    dark.write_bytes(b"dark")
    cache = AnalysisCache(tmp_path / "analysis.json")
    seed(cache, result(blue), result(dark, vibe="Dark / Moody", score=0.9))

    matches = search_cache(cache, ImageQuery(vibe="Retro Blue", min_score=0.8))
    assert [item.path for item in matches] == [blue]


def test_search_matches_filename_case_insensitively(tmp_path: Path) -> None:
    image = tmp_path / "Billie Eilish" / "Ocean Eyes.JPG"
    image.parent.mkdir()
    image.write_bytes(b"image")
    cache = AnalysisCache(tmp_path / "analysis.json")
    seed(cache, result(image))

    assert search_cache(cache, ImageQuery(path_contains="billie eilish"))[0].path == image
    assert search_cache(cache, ImageQuery(path_contains="missing")) == ()


def test_search_applies_dimension_filters(tmp_path: Path) -> None:
    low = tmp_path / "low.jpg"
    high = tmp_path / "high.jpg"
    low.write_bytes(b"low")
    high.write_bytes(b"high")
    cache = AnalysisCache(tmp_path / "analysis.json")
    seed(cache, result(low, brightness=0.3), result(high, brightness=0.8))

    matches = search_cache(cache, ImageQuery(min_brightness=0.7))
    assert [item.path for item in matches] == [high]


def test_search_excludes_text_heavy_images(tmp_path: Path) -> None:
    photo = tmp_path / "photo.jpg"
    screenshot = tmp_path / "screenshot.jpg"
    photo.write_bytes(b"photo")
    screenshot.write_bytes(b"screenshot")
    cache = AnalysisCache(tmp_path / "analysis.json")
    seed(cache, result(photo, text=0.2), result(screenshot, text=0.9))

    matches = search_cache(cache, ImageQuery(max_text_likelihood=0.5))
    assert [item.path for item in matches] == [photo]


def test_search_sorts_by_best_score_and_supports_limit(tmp_path: Path) -> None:
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    cache = AnalysisCache(tmp_path / "analysis.json")
    seed(cache, result(first, score=0.5), result(second, score=0.9))

    matches = search_cache(cache, ImageQuery(limit=1))
    assert [item.path for item in matches] == [second]
