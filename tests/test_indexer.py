from pathlib import Path

from PIL import Image

from vibesorter import indexer
from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.vibes import VibeScore


def _features(path: Path) -> ImageFeatures:
    return ImageFeatures(
        path=path,
        average_rgb=(20, 30, 40),
        average_hsv=(0.1, 0.2, 0.3),
        brightness=0.2,
        saturation=0.3,
        contrast=0.4,
        warm_ratio=0.1,
        cool_ratio=0.2,
        grayscale_ratio=0.0,
        dark_ratio=0.8,
        light_ratio=0.1,
        text_likelihood=0.0,
        colors=(ColorSample((20, 30, 40), 1.0),),
    )


def test_index_folder_populates_sqlite_and_reuses_unchanged_images(tmp_path, monkeypatch):
    first = tmp_path / "first.png"
    second = tmp_path / "nested" / "second.png"
    second.parent.mkdir()
    Image.new("RGB", (2, 2), (10, 20, 30)).save(first)
    Image.new("RGB", (2, 2), (30, 20, 10)).save(second)

    calls = []

    class Result:
        def __init__(self, path):
            self.features = _features(path)
            self.scores = (VibeScore("Dark / Moody", 0.8), VibeScore("Soft / Pastel", 0.4))

    def fake_analyze(path):
        calls.append(path)
        return Result(path)

    monkeypatch.setattr(indexer, "analyze_image", fake_analyze)

    first_run = indexer.index_folder(tmp_path, workers=2)
    assert first_run["total"] == 2
    assert first_run["analyzed"] == 2
    assert first_run["reused"] == 0
    assert first_run["skipped"] == 0
    assert len(calls) == 2

    db = tmp_path / ".vibesorter" / "analysis.db"
    with AnalysisCache(db) as cache:
        assert len(cache.entries()) == 2
        assert cache.get(first) is not None
        assert cache.get(second) is not None

    second_run = indexer.index_folder(tmp_path, workers=2)
    assert second_run["analyzed"] == 0
    assert second_run["reused"] == 2
    assert len(calls) == 2


def test_index_folder_reanalyzes_changed_and_removes_deleted_images(tmp_path, monkeypatch):
    changed = tmp_path / "changed.png"
    deleted = tmp_path / "deleted.png"
    Image.new("RGB", (2, 2), (10, 20, 30)).save(changed)
    Image.new("RGB", (2, 2), (30, 20, 10)).save(deleted)

    calls = []

    class Result:
        def __init__(self, path):
            self.features = _features(path)
            self.scores = (VibeScore("Retro Blue", 0.7),)

    monkeypatch.setattr(indexer, "analyze_image", lambda path: (calls.append(path) or Result(path)))

    indexer.index_folder(tmp_path, workers=1)
    calls.clear()
    deleted.unlink()
    changed.write_bytes(changed.read_bytes() + b"changed")

    result = indexer.index_folder(tmp_path, workers=1)

    assert result["analyzed"] == 1
    assert result["reused"] == 0
    assert result["removed"] == 1
    assert calls == [changed]

    with AnalysisCache(tmp_path / ".vibesorter" / "analysis.db") as cache:
        assert cache.get(changed) is not None
        assert cache.get(deleted) is None
