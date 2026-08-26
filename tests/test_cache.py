from __future__ import annotations

import os
from pathlib import Path

from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.vibes import VibeScore


def sample_features(path: Path) -> ImageFeatures:
    return ImageFeatures(path, (10, 20, 30), (0.5, 0.6, 0.7), 0.7, 0.6, 0.3, 0.1, 0.8, 0.05, 0.2, 0.4, 0.1, (ColorSample((8, 18, 28), 1.0),))


def test_cache_round_trip(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"image")
    cache = AnalysisCache(tmp_path / ".vibesorter" / "analysis.json")
    features = sample_features(image)
    scores = (VibeScore("Retro Blue", 0.82), VibeScore("Dark / Moody", 0.41))
    cache.set(image, features, scores)
    cache.save()
    restored = AnalysisCache(cache.path).get(image)
    assert restored is not None
    assert restored == (features, scores)


def test_changed_file_invalidates_entry(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"image")
    cache = AnalysisCache(tmp_path / "analysis.json")
    cache.set(image, sample_features(image), (VibeScore("Retro Blue", 0.82),))
    cache.save()
    image.write_bytes(b"a different image")
    os.utime(image, None)
    assert AnalysisCache(cache.path).get(image) is None


def test_missing_entries_can_be_pruned(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"image")
    cache = AnalysisCache(tmp_path / "analysis.json")
    cache.set(image, sample_features(image), (VibeScore("Retro Blue", 0.82),))
    image.unlink()
    assert cache.remove_missing() == 1
