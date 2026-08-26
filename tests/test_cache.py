from __future__ import annotations

from pathlib import Path

from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.vibes import VibeScore


def sample_features(path: Path) -> ImageFeatures:
    return ImageFeatures(
        path=path,
        average_rgb=(10, 20, 30),
        average_hsv=(0.5, 0.6, 0.7),
        brightness=0.7,
        saturation=0.6,
        contrast=0.3,
        warm_ratio=0.1,
        cool_ratio=0.8,
        grayscale_ratio=0.05,
        dark_ratio=0.2,
        light_ratio=0.4,
        text_likelihood=0.1,
        colors=(ColorSample((8, 18, 28), 1.0),),
    )


def test_cache_round_trip(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    cache = AnalysisCache(tmp_path / ".vibesorter" / "analysis.json")
    features = sample_features(image)
    scores = (VibeScore("Retro Blue", 0.82), VibeScore("Dark / Moody", 0.41))

    cache.set(image, features, scores)
    cache.save()

    restored = AnalysisCache(cache.path).get(image)
    assert restored is not None
    restored_features, restored_scores = restored
    assert restored_features == features
    assert restored_scores == scores


def test_corrupt_cache_is_ignored(tmp_path: Path) -> None:
    cache_path = tmp_path / "analysis.json"
    cache_path.write_text("not-json", encoding="utf-8")
    assert AnalysisCache(cache_path).get(tmp_path / "missing.jpg") is None
