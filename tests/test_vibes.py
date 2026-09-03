from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.features import ImageFeatures, extract_features
from vibesorter.vibes import VibeScore, classify, confidence_score, is_confident, score_vibe_contributions, score_vibes


def make_image(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (32, 32), color).save(path)


def test_extract_features_is_small_and_stable(tmp_path: Path) -> None:
    image = tmp_path / "blue.png"
    make_image(image, (30, 80, 180))

    features = extract_features(image)

    assert features.path == image
    assert features.average_rgb == (30, 80, 180)
    assert len(features.colors) <= 6
    assert abs(sum(color.proportion for color in features.colors) - 1.0) < 1e-9
    assert features.cool_ratio > features.warm_ratio


def test_extractor_handles_rgba_images(tmp_path: Path) -> None:
    image = tmp_path / "transparent.png"
    Image.new("RGBA", (20, 20), (255, 0, 0, 80)).save(image)

    features = extract_features(image)

    assert features.average_rgb == (255, 0, 0)
    assert features.warm_ratio > 0.9


def test_vibe_scores_are_sorted_and_complete(tmp_path: Path) -> None:
    image = tmp_path / "red.png"
    make_image(image, (220, 30, 20))

    features = extract_features(image)
    scores = score_vibes(features)

    assert len(scores) == 7
    assert scores[0].score >= scores[-1].score
    assert {result.name for result in scores} == {
        "Retro Blue", "Red / Warm", "Green & Black", "Black & White",
        "Soft / Pastel", "Dark / Moody", "Bright / Colorful",
    }
    assert classify(features) == scores[0]
    assert scores[0].name == "Red / Warm"


def test_confidence_rewards_clear_separation() -> None:
    clear = (VibeScore("Red / Warm", 0.82), VibeScore("Bright / Colorful", 0.55))
    close = (VibeScore("Red / Warm", 0.82), VibeScore("Bright / Colorful", 0.78))

    assert confidence_score(clear) > confidence_score(close)
    assert 0 <= confidence_score(clear) <= 1


def test_ambiguous_winner_requires_review() -> None:
    scores = (
        VibeScore("Soft / Pastel", 0.61),
        VibeScore("Retro Blue", 0.58),
    )

    assert not is_confident(scores)


def test_clear_winner_can_be_sorted_automatically() -> None:
    scores = (
        VibeScore("Red / Warm", 0.82),
        VibeScore("Bright / Colorful", 0.70),
    )

    assert is_confident(scores)


def _feature_snapshot(*, brightness: float, saturation: float, contrast: float, dark: float, light: float, cool: float, regions=()):
    return ImageFeatures(
        path=Path("fixture.png"), average_rgb=(84, 101, 90),
        average_hsv=(0.35, saturation, brightness), brightness=brightness,
        saturation=saturation, contrast=contrast, warm_ratio=0.15,
        cool_ratio=cool, grayscale_ratio=0.18, dark_ratio=dark,
        light_ratio=light, text_likelihood=0.3, colors=(), regions=regions,
        center_brightness_delta=0.18, center_saturation_delta=-0.06,
    )


def test_dark_muted_fixture_is_not_promoted_to_soft_pastel() -> None:
    features = _feature_snapshot(
        brightness=0.4079, saturation=0.2811, contrast=0.1977,
        dark=0.3532, light=0.0174, cool=0.2122,
    )
    scores = dict((score.name, score.score) for score in score_vibes(features))
    assert scores["Soft / Pastel"] < 0.45


def test_regional_cool_signal_can_support_retro_blue() -> None:
    from vibesorter.features import SpatialRegion
    features = _feature_snapshot(
        brightness=0.45, saturation=0.40, contrast=0.40,
        dark=0.40, light=0.30, cool=0.20,
        regions=(
            SpatialRegion(0.30, 0.26, 0.03, 0.08),
            SpatialRegion(0.31, 0.29, 0.32, 0.00),
            SpatialRegion(0.47, 0.34, 0.11, 0.66),
            SpatialRegion(0.55, 0.23, 0.15, 0.20),
        ),
    )
    scores = score_vibes(features)
    assert scores[0].name == "Retro Blue"


def test_pastel_darkness_penalty_is_explainable() -> None:
    features = _feature_snapshot(
        brightness=0.4079, saturation=0.2811, contrast=0.1977,
        dark=0.3532, light=0.0174, cool=0.2122,
    )
    contributions = score_vibe_contributions(features)["Soft / Pastel"]
    assert contributions["darkness_penalty"] < 0
    assert sum(contributions.values()) < 0.45
