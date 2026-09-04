from __future__ import annotations

from pathlib import Path

from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.pipeline import AnalysisResult
from vibesorter.profile import AttributeValue, ImageProfile
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
    assert [item.path for item in search_cache(cache, ImageQuery(vibe="Retro Blue", min_score=0.8))] == [blue]


def test_search_matches_filename_case_insensitively(tmp_path: Path) -> None:
    image = tmp_path / "Billie Eilish" / "Ocean Eyes.JPG"
    image.parent.mkdir(); image.write_bytes(b"image")
    cache = AnalysisCache(tmp_path / "analysis.json"); seed(cache, result(image))
    assert search_cache(cache, ImageQuery(path_contains="billie eilish"))[0].path == image
    assert search_cache(cache, ImageQuery(path_contains="missing")) == ()


def test_search_applies_dimension_filters(tmp_path: Path) -> None:
    low, high = tmp_path / "low.jpg", tmp_path / "high.jpg"
    low.write_bytes(b"low"); high.write_bytes(b"high")
    cache = AnalysisCache(tmp_path / "analysis.json"); seed(cache, result(low, brightness=0.3), result(high, brightness=0.8))
    assert [item.path for item in search_cache(cache, ImageQuery(min_brightness=0.7))] == [high]


def test_search_excludes_text_heavy_images(tmp_path: Path) -> None:
    photo, screenshot = tmp_path / "photo.jpg", tmp_path / "screenshot.jpg"
    photo.write_bytes(b"photo"); screenshot.write_bytes(b"screenshot")
    cache = AnalysisCache(tmp_path / "analysis.json"); seed(cache, result(photo, text=0.2), result(screenshot, text=0.9))
    assert [item.path for item in search_cache(cache, ImageQuery(max_text_likelihood=0.5))] == [photo]


def test_search_sorts_by_best_score_and_supports_limit(tmp_path: Path) -> None:
    first, second = tmp_path / "first.jpg", tmp_path / "second.jpg"
    first.write_bytes(b"first"); second.write_bytes(b"second")
    cache = AnalysisCache(tmp_path / "analysis.json"); seed(cache, result(first, score=0.5), result(second, score=0.9))
    assert [item.path for item in search_cache(cache, ImageQuery(limit=1))] == [second]


def test_search_combines_families_and_allows_multiple_colors_and_vibes(tmp_path: Path) -> None:
    red_cool = tmp_path / "red-cool.jpg"
    warm_blue = tmp_path / "warm-blue.jpg"
    red_cool.write_bytes(b"red-cool"); warm_blue.write_bytes(b"warm-blue")
    cache = AnalysisCache(tmp_path / "analysis.json")
    first, second = result(red_cool), result(warm_blue)
    seed(cache, first, second)
    cache.set_profile(red_cool, ImageProfile(media_type=AttributeValue("photograph", .99), colors=(AttributeValue("red", .94), AttributeValue("blue", .63)), temperature=AttributeValue("cool", .88), saturation=AttributeValue("muted", .79), brightness=AttributeValue("dark", .9), vibes=(AttributeValue("retro", .72), AttributeValue("moody", .67))))
    cache.set_profile(warm_blue, ImageProfile(media_type=AttributeValue("photograph", .99), colors=(AttributeValue("blue", .94),), temperature=AttributeValue("warm", .88), saturation=AttributeValue("vibrant", .9), brightness=AttributeValue("bright", .9), vibes=(AttributeValue("playful", .8),)))
    cache.save()
    query = ImageQuery(media_type="photograph", colors=("red", "blue"), temperature="cool", vibes=("retro", "moody"))
    assert search_cache(cache, query)[0].path == red_cool
