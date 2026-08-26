import pytest

from vibesorter.diagnostics import diagnose
from vibesorter.features import extract_features


def test_diagnostic_contains_winner_and_margin(image_factory):
    path = image_factory("sample.png", (30, 80, 180))
    result = diagnose(extract_features(path))
    assert result.winner.name
    assert result.margin >= 0
    assert 0 <= result.confidence <= 1


def test_negative_ambiguity_margin_is_rejected(image_factory):
    path = image_factory("sample.png")
    with pytest.raises(ValueError):
        diagnose(extract_features(path), ambiguity_margin=-0.1)
