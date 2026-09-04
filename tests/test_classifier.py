from pathlib import Path

from vibesorter.classifier import classify_profile
from vibesorter.features import ColorSample, ImageFeatures


def features(**overrides) -> ImageFeatures:
    values = dict(
        path=Path("image.jpg"), average_rgb=(180, 40, 60), average_hsv=(0.98, 0.78, 0.70),
        brightness=0.70, saturation=0.78, contrast=0.30, warm_ratio=0.10, cool_ratio=0.45,
        grayscale_ratio=0.05, dark_ratio=0.10, light_ratio=0.30, text_likelihood=0.05,
        colors=(ColorSample((190, 40, 60), 0.65), ColorSample((40, 70, 180), 0.25)),
    )
    values.update(overrides)
    return ImageFeatures(**values)


def test_red_and_cool_are_independent_attributes():
    profile = classify_profile(features())
    assert profile.colors[0].value == "red"
    assert profile.temperature.value == "cool"
    assert profile.saturation.value == "vibrant"
    assert profile.brightness.value == "bright"


def test_multiple_colors_can_be_assigned():
    profile = classify_profile(features())
    assert {item.value for item in profile.colors} >= {"red", "blue"}


def test_dark_images_get_dark_brightness_attribute():
    profile = classify_profile(features(brightness=0.20, dark_ratio=0.70, light_ratio=0.02))
    assert profile.brightness.value == "dark"


def test_classifier_returns_profile_not_single_vibe():
    profile = classify_profile(features())
    assert profile.media_type is not None
    assert profile.temperature is not None
    assert profile.saturation is not None
    assert profile.brightness is not None
