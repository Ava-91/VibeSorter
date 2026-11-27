from pathlib import Path

import pytest
from PIL import Image

from vibesorter.classifier import classify_profile
from vibesorter.features import extract_features
from vibesorter.pipeline import AnalysisResult
from vibesorter.vibes import ConfidenceThresholds, VibeScore, assess_confidence


def test_empty_or_missing_scores_abstain():
    result = assess_confidence(())
    assert result.category == "uncertain"
    assert result.label is None
    assert "No usable" in result.reason


def test_low_evidence_abstains_with_explanation():
    result = assess_confidence((VibeScore("retro", 0.42), VibeScore("dreamy", 0.18)))
    assert result.category == "uncertain"
    assert result.label is None
    assert "below" in result.reason


def test_close_competing_scores_abstain():
    result = assess_confidence((VibeScore("retro", 0.70), VibeScore("dreamy", 0.65)))
    assert result.category == "uncertain"
    assert result.label is None
    assert "too close" in result.reason


def test_possible_and_strong_evidence_have_labels():
    possible = assess_confidence((VibeScore("retro", 0.62), VibeScore("dreamy", 0.50)))
    strong = assess_confidence((VibeScore("retro", 0.84), VibeScore("dreamy", 0.60)))
    assert (possible.category, possible.label) == ("possible", "retro")
    assert (strong.category, strong.label) == ("strong", "retro")
    assert 0 <= strong.ranking_signal <= 1


def test_possible_threshold_boundaries_are_inclusive():
    at_boundary = assess_confidence((VibeScore("retro", 0.55), VibeScore("dreamy", 0.47)))
    below_margin = assess_confidence((VibeScore("retro", 0.55), VibeScore("dreamy", 0.4701)))
    assert at_boundary.category == "possible"
    assert below_margin.category == "uncertain"


def test_thresholds_are_configurable_in_one_policy_object():
    thresholds = ConfidenceThresholds(possible_score=0.4, possible_margin=0.02)
    result = assess_confidence(
        (VibeScore("retro", 0.45), VibeScore("dreamy", 0.40)),
        thresholds=thresholds,
    )
    assert result.category == "possible"


def test_invalid_confidence_thresholds_are_rejected():
    with pytest.raises(ValueError):
        ConfidenceThresholds(possible_score=1.2)
    with pytest.raises(ValueError):
        ConfidenceThresholds(possible_score=0.6, strong_score=0.5)


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
