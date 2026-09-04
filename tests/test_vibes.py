from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.features import ImageFeatures, extract_features
from vibesorter.taxonomy import Vibe
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


def test_vibe_scores_are_canonical_and_sorted(tmp_path: Path) -> None:
    image = tmp_path / "red.png"
    make_image(image, (220, 30, 20))
    scores = score_vibes(extract_features(image))
    assert len(scores) == len(Vibe)
    assert scores[0].score >= scores[-1].score
    assert {result.name for result in scores} == {item.value for item in Vibe}
    assert classify(extract_features(image)) == scores[0]


def test_confidence_rewards_clear_separation() -> None:
    clear = (VibeScore("retro", 0.82), VibeScore("dreamy", 0.55))
    close = (VibeScore("retro", 0.82), VibeScore("dreamy", 0.78))
    assert confidence_score(clear) > confidence_score(close)
    assert 0 <= confidence_score(clear) <= 1


def test_ambiguous_winner_requires_review() -> None:
    scores = (VibeScore("soft", 0.61), VibeScore("retro", 0.58))
    assert not is_confident(scores)


def test_clear_winner_can_be_sorted_automatically() -> None:
    scores = (VibeScore("retro", 0.82), VibeScore("playful", 0.70))
    assert is_confident(scores)


def test_contributions_are_explainable() -> None:
    features = ImageFeatures(
        path=Path("fixture.png"),
        average_rgb=(84, 101, 90),
        average_hsv=(0.35, 0.28, 0.41),
        brightness=0.41,
        saturation=0.28,
        contrast=0.20,
        warm_ratio=0.15,
        cool_ratio=0.21,
        grayscale_ratio=0.18,
        dark_ratio=0.35,
        light_ratio=0.02,
        text_likelihood=0.3,
        colors=(),
        regions=(),
        center_brightness_delta=0.18,
        center_saturation_delta=-0.06,
    )
    contributions = score_vibe_contributions(features)
    scores = {score.name: score.score for score in score_vibes(features)}
    assert set(contributions) == set(scores)
    for name, values in contributions.items():
        assert round(sum(values.values()), 4) == scores[name]


def test_canonical_vibes_never_emit_compound_labels() -> None:
    forbidden = {
        "Retro Blue",
        "Red / Warm",
        "Green & Black",
        "Black & White",
        "Soft / Pastel",
        "Dark / Moody",
        "Bright / Colorful",
        "Neutral / Photo Dump",
    }
    for score in score_vibes(
        ImageFeatures(
            Path("fixture.png"),
            (100, 120, 140),
            (0.5, 0.3, 0.5),
            0.5,
            0.3,
            0.4,
            0.3,
            0.3,
            0.2,
            0.3,
            0.3,
            0.1,
            (),
        )
    ):
        assert score.name not in forbidden
