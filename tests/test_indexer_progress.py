from pathlib import Path

from PIL import Image

from vibesorter import indexer
from vibesorter.cache import AnalysisCache
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.vibes import VibeScore


def _features(path: Path) -> ImageFeatures:
    return ImageFeatures(path, (20, 30, 40), (0.1, 0.2, 0.3), 0.2, 0.3, 0.4, 0.1, 0.2, 0.0, 0.8, 0.1, 0.0, (ColorSample((20, 30, 40), 1.0),))


def test_index_folder_reports_progress_phases_and_counts(tmp_path, monkeypatch):
    image = tmp_path / "one.png"
    Image.new("RGB", (2, 2), (10, 20, 30)).save(image)
    events = []

    class Result:
        features = _features(image)
        scores = (VibeScore("Dark / Moody", 0.8),)

    monkeypatch.setattr(indexer, "analyze_image", lambda path: Result())
    result = indexer.index_folder(tmp_path, workers=1, progress=events.append)

    assert [event["phase"] for event in events] == ["scan", "analyze", "analyze", "complete"]
    assert events[0]["total"] == 1
    assert events[-1]["analyzed"] == result["analyzed"] == 1


def test_index_folder_reports_skips_in_progress(tmp_path, monkeypatch):
    image = tmp_path / "broken.png"
    image.write_bytes(b"not-an-image")
    events = []
    monkeypatch.setattr(indexer, "analyze_image", lambda path: (_ for _ in ()).throw(ValueError("bad image")))

    result = indexer.index_folder(tmp_path, workers=1, progress=events.append)

    assert result["skipped"] == 1
    assert events[-2]["phase"] == "analyze"
    assert events[-2]["skipped"] == 1
    assert events[-1]["phase"] == "complete"
