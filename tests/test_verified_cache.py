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



def test_bulk_verification_checks_all_hashes_without_per_item_cache_lookups(tmp_path: Path, monkeypatch):
    import vibesorter.verified_cache as verified_cache_module

    paths = [tmp_path / f"photo-{index}.jpg" for index in range(3)]
    cache = VerifiedAnalysisCache(tmp_path / "analysis.db")
    for path in paths:
        path.write_bytes(b"same-size-bytes")
        cache.set(path, _features(path), (VibeScore("Retro Blue", 0.8),))
    cache.save()

    calls = []
    real_digest = verified_cache_module._digest

    def count_digest(path: Path) -> str:
        calls.append(path)
        return real_digest(path)

    monkeypatch.setattr(verified_cache_module, "_digest", count_digest)
    assert cache.get_verified_many(paths) == set(paths)
    assert len(calls) == len(paths)

    original_mtime = paths[0].stat().st_mtime_ns
    paths[0].write_bytes(b"new--size-bytes")
    os.utime(paths[0], ns=(original_mtime, original_mtime))
    verified = cache.get_verified_many(paths)
    assert paths[0] not in verified
    assert set(paths[1:]).issubset(verified)



def test_changed_during_analysis_preserves_previous_cache_entry(tmp_path: Path):
    from vibesorter.verified_cache import _digest

    image = tmp_path / "photo.jpg"
    image.write_bytes(b"original")
    cache = VerifiedAnalysisCache(tmp_path / "analysis.db")
    original_features = _features(image)
    original_scores = (VibeScore("Retro Blue", 0.8),)
    assert cache.set(image, original_features, original_scores)
    cache.save()

    original_identity = (image.stat().st_size, image.stat().st_mtime_ns)
    original_digest = _digest(image)
    previous = cache.get(image)

    image.write_bytes(b"changed!")
    changed_features = _features(image)
    changed_scores = (VibeScore("Dark / Moody", 0.9),)

    assert not cache.set(
        image,
        changed_features,
        changed_scores,
        expected_identity=original_identity,
        expected_digest=original_digest,
    )
    assert cache.get(image) == previous
    assert cache.get_verified(image) is None
