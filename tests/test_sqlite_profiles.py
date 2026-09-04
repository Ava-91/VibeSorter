from pathlib import Path

import pytest

from vibesorter.profile import AttributeValue, ImageProfile
from vibesorter.sqlite_cache import SQLiteAnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.vibes import VibeScore


def make_features(path: Path) -> ImageFeatures:
    return ImageFeatures(
        path=path, average_rgb=(120, 80, 90), average_hsv=(0.98, 0.33, 0.47),
        brightness=0.47, saturation=0.33, contrast=0.2, warm_ratio=0.2, cool_ratio=0.2,
        grayscale_ratio=0.1, dark_ratio=0.2, light_ratio=0.1, text_likelihood=0.1,
        colors=(ColorSample((120, 80, 90), 1.0),),
    )


def make_profile() -> ImageProfile:
    return ImageProfile(
        media_type=AttributeValue("photograph", 1.0),
        colors=(AttributeValue("red", 0.9), AttributeValue("blue", 0.8)),
        temperature=AttributeValue("cool", 0.9),
        saturation=AttributeValue("muted", 0.9),
        brightness=AttributeValue("mid", 0.9),
        vibes=(AttributeValue("retro", 0.8), AttributeValue("moody", 0.7)),
    )


def test_profile_round_trips_separately_from_raw_features(tmp_path):
    image = tmp_path / "a.jpg"
    image.write_bytes(b"image")
    with SQLiteAnalysisCache(tmp_path / "analysis.db") as cache:
        features = make_features(image)
        cache.set(image, features, (VibeScore("Retro Blue", 0.5),))
        cache.set_profile(image, make_profile())
        assert cache.get(image) is not None
        assert cache.get_profile(image) == make_profile()


def test_profile_requires_existing_image_analysis_record(tmp_path):
    with SQLiteAnalysisCache(tmp_path / "analysis.db") as cache:
        with pytest.raises(ValueError, match="before its image analysis record"):
            cache.set_profile(tmp_path / "missing.jpg", make_profile())


def test_profile_table_is_removed_with_image_record(tmp_path):
    image = tmp_path / "a.jpg"
    image.write_bytes(b"image")
    with SQLiteAnalysisCache(tmp_path / "analysis.db") as cache:
        cache.set(image, make_features(image), (VibeScore("Retro Blue", 0.5),))
        cache.set_profile(image, make_profile())
        image.unlink()
        assert cache.remove_missing() == 1
        assert cache.get_profile(image) is None
