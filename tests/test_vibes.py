from __future__ import annotations

from pathlib import Path

from PIL import Image

from vibesorter.features import extract_features
from vibesorter.vibes import VibeScore, classify, is_confident, score_vibes


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
