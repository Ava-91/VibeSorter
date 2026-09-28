import os
from pathlib import Path

from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.verified_cache import VerifiedAnalysisCache
from vibesorter.vibes import VibeScore


def _features(path: Path) -> ImageFeatures:
    return ImageFeatures(path, (1, 2, 3), (0.1, 0.2, 0.3), 0.2, 0.3, 0.4, 0.1, 0.2, 0.0, 0.8, 0.1, 0.0, (ColorSample((1, 2, 3), 1.0),))


def test_verified_cache_detects_same_size_same_mtime_content_change(tmp_path: Path):
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"AAAA")
    cache = VerifiedAnalysisCache(tmp_path / "analysis.db")
    cache.set(image, _features(image), (VibeScore("Retro Blue", 0.8),))
    cache.save()
    original_mtime = image.stat().st_mtime_ns

    image.write_bytes(b"BBBB")
    os.utime(image, ns=(original_mtime, original_mtime))

    assert cache.get_verified(image) is None
