from __future__ import annotations

from dataclasses import dataclass

from .features import ImageFeatures


VIBES = (
    "Retro Blue",
    "Red / Warm",
    "Green & Black",
    "Black & White",
    "Soft / Pastel",
    "Dark / Moody",
    "Bright / Colorful",
)

# A top score by itself is not enough to justify moving a file. These
# thresholds keep ambiguous images in the preview-only review bucket.
MIN_CONFIDENCE = 0.60
MIN_MARGIN = 0.08
REVIEW_VIBE = "Needs Review"


@dataclass(frozen=True, slots=True)
class VibeScore:
    name: str
    score: float


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_vibes(features: ImageFeatures) -> tuple[VibeScore, ...]:
    """Score atmospheric categories from visual features, rather than recognizing objects."""
    r, g, b = (value / 255.0 for value in features.average_rgb)
    brightness = features.brightness
    saturation = features.saturation
    contrast = features.contrast
    gray = features.grayscale_ratio
    dark = features.dark_ratio
    light = features.light_ratio

    scores = {
        "Retro Blue": _clamp(
            0.38 * features.cool_ratio
            + 0.24 * (1 - saturation)
            + 0.20 * _clamp((b - r + 0.25) / 0.65)
            + 0.18 * _clamp(1 - abs(brightness - 0.52) / 0.52)
        ),
        "Red / Warm": _clamp(
            0.52 * features.warm_ratio
            + 0.25 * _clamp((r - b + 0.20) / 0.70)
            + 0.13 * saturation
            + 0.10 * _clamp(1 - dark)
        ),
        "Green & Black": _clamp(
            0.45 * _clamp((g - r + 0.15) / 0.55)
            + 0.30 * dark
            + 0.15 * saturation
            + 0.10 * _clamp((g - b + 0.15) / 0.55)
        ),
        "Black & White": _clamp(
            0.62 * gray
            + 0.23 * contrast
            + 0.15 * _clamp(dark + light)
        ),
        "Soft / Pastel": _clamp(
            0.34 * (1 - saturation)
            + 0.32 * light
            + 0.20 * _clamp(1 - contrast)
            + 0.14 * _clamp(brightness)
        ),
        "Dark / Moody": _clamp(
            0.48 * dark
            + 0.25 * contrast
            + 0.17 * saturation
            + 0.10 * _clamp(1 - brightness)
        ),
        "Bright / Colorful": _clamp(
            0.38 * light
            + 0.34 * saturation
            + 0.18 * brightness
            + 0.10 * _clamp(1 - gray)
        ),
    }

    return tuple(sorted(
        (VibeScore(name, round(score, 4)) for name, score in scores.items()),
        key=lambda result: result.score,
        reverse=True,
    ))


def is_confident(scores: tuple[VibeScore, ...]) -> bool:
    """Return whether the winner is sufficiently separated from its runner-up."""
    if len(scores) < 2:
        return bool(scores) and scores[0].score >= MIN_CONFIDENCE
    return (
        scores[0].score >= MIN_CONFIDENCE
        and scores[0].score - scores[1].score >= MIN_MARGIN
    )


def classify(features: ImageFeatures) -> VibeScore:
    """Return the strongest first-pass vibe; ambiguity is checked separately."""
    return score_vibes(features)[0]
