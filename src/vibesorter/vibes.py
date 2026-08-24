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


MIN_CONFIDENT_SCORE = 0.60
MIN_CONFIDENT_MARGIN = 0.08
CONFIDENCE_MARGIN_SCALE = 0.25


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


def confidence_score(
    scores: tuple[VibeScore, ...],
    *,
    margin_scale: float = CONFIDENCE_MARGIN_SCALE,
) -> float:
    """Estimate classification confidence from winner strength and separation.

    This is a heuristic confidence indicator, not a probability. It rewards a
    strong winner and a clear gap over the runner-up, making it more useful for
    deciding which images are safe to auto-sort.
    """
    if not scores:
        return 0.0
    if margin_scale <= 0:
        raise ValueError("margin_scale must be greater than 0")
    winner = scores[0].score
    runner_up = scores[1].score if len(scores) > 1 else 0.0
    margin = max(0.0, winner - runner_up)
    separation = _clamp(margin / margin_scale)
    return round(_clamp(0.65 * winner + 0.35 * separation), 4)


def is_confident(scores: tuple[VibeScore, ...], *,
                 min_score: float = MIN_CONFIDENT_SCORE,
                 min_margin: float = MIN_CONFIDENT_MARGIN) -> bool:
    """Return whether the winner is strong enough to treat as an automatic classification."""
    if not scores:
        return False
    if not 0 <= min_score <= 1:
        raise ValueError("min_score must be between 0 and 1")
    if min_margin < 0:
        raise ValueError("min_margin must be non-negative")
    winner = scores[0]
    runner_up = scores[1] if len(scores) > 1 else None
    margin = winner.score if runner_up is None else winner.score - runner_up.score
    return winner.score >= min_score and margin >= min_margin


def classify(features: ImageFeatures) -> VibeScore:
    """Return the strongest first-pass vibe. Internal scores remain available."""
    return score_vibes(features)[0]
