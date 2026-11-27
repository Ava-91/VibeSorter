from pathlib import Path

from PIL import Image

from vibesorter.classifier import classify_profile
from vibesorter.features import extract_features
from vibesorter.pipeline import AnalysisResult
from vibesorter.vibes import VibeScore


def test_analysis_result_withholds_uncertain_primary_label(tmp_path: Path):
    path = tmp_path / "gray.png"
    Image.new("RGB", (16, 16), (128, 128, 128)).save(path)
    features = extract_features(path)
    scores = (VibeScore("retro", 0.70), VibeScore("dreamy", 0.65))
    result = AnalysisResult(path, features, scores[0], scores)
    assert result.suggested_label is None
    assert result.assessment.category == "uncertain"
    assert result.vibes == ()


def test_profile_does_not_store_uncertain_vibe_labels(tmp_path: Path, monkeypatch):
    path = tmp_path / "gray.png"
    Image.new("RGB", (16, 16), (128, 128, 128)).save(path)
    features = extract_features(path)
    monkeypatch.setattr(
        "vibesorter.classifier.score_vibes",
        lambda _features: (VibeScore("retro", 0.70), VibeScore("dreamy", 0.65)),
    )
    profile = classify_profile(features)
    assert profile.vibes == ()
