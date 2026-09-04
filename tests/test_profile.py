import pytest

from vibesorter.profile import AttributeValue, ImageProfile


def test_profile_supports_multiple_colors_and_vibes():
    profile = ImageProfile(
        media_type=AttributeValue("photograph", 0.99),
        colors=(AttributeValue("red", 0.94), AttributeValue("blue", 0.63)),
        temperature=AttributeValue("cool", 0.88),
        saturation=AttributeValue("muted", 0.79),
        brightness=AttributeValue("dark", 0.91),
        vibes=(AttributeValue("retro", 0.72), AttributeValue("moody", 0.67)),
    )
    restored = ImageProfile.from_json(profile.to_json())
    assert restored == profile


def test_duplicate_multi_value_is_rejected():
    with pytest.raises(ValueError, match="duplicate colors"):
        ImageProfile(colors=(AttributeValue("red", 0.9), AttributeValue("red", 0.8)))


def test_invalid_confidence_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        AttributeValue("red", 1.1)


def test_legacy_compound_labels_are_rejected():
    with pytest.raises(ValueError, match="legacy compound label"):
        AttributeValue("Red / Warm", 0.9)
