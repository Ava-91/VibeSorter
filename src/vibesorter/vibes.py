from __future__ import annotations

from dataclasses import dataclass

from .features import ImageFeatures
from .taxonomy import Vibe

CONFIDENCE_MARGIN_SCALE = 0.25

@dataclass(frozen=True, slots=True)
class ConfidenceThresholds:
    """Single policy point for heuristic label abstention."""
    possible_score: float = 0.55
    possible_margin: float = 0.08
    strong_score: float = 0.72
    strong_margin: float = 0.16

    def __post_init__(self) -> None:
        values = (self.possible_score, self.possible_margin, self.strong_score, self.strong_margin)
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("confidence thresholds must be between 0 and 1")
        if self.strong_score < self.possible_score or self.strong_margin < self.possible_margin:
            raise ValueError("strong thresholds must be at least as strict as possible thresholds")


DEFAULT_CONFIDENCE_THRESHOLDS = ConfidenceThresholds()
MIN_CONFIDENT_SCORE = DEFAULT_CONFIDENCE_THRESHOLDS.possible_score
MIN_CONFIDENT_MARGIN = DEFAULT_CONFIDENCE_THRESHOLDS.possible_margin
DEFAULT_VIBE_THRESHOLD = 0.55
DEFAULT_VIBE_MARGIN = 0.08

VIBE_MAX_SCORES = {
    "retro": 0.80,
    "dreamy": 0.78,
    "soft": 0.80,
    "moody": 0.86,
    "minimal": 0.82,
    "cozy": 0.86,
    "cinematic": 0.80,
    "playful": 0.84,
    "edgy": 0.86,
    "romantic": 0.78,
}


@dataclass(frozen=True, slots=True)
class VibeScore:
    name: str
    score: float


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    category: str
    label: str | None
    score: float
    margin: float
    ranking_signal: float
    reason: str


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_components(features: ImageFeatures) -> dict[str, dict[str, float]]:
    """Score only canonical, independent aesthetic concepts."""
    brightness = features.brightness
    saturation = features.saturation
    contrast = features.contrast
    dark = features.dark_ratio
    light = features.light_ratio
    warm = features.warm_ratio
    cool = features.cool_ratio
    gray = features.grayscale_ratio
    text = features.text_likelihood
    blue = features.average_rgb[2] / 255.0
    red = features.average_rgb[0] / 255.0
    regional_cool = max((region.cool_ratio for region in features.regions), default=cool)

    return {
        "retro": {
            "cool_signal": 0.24 * cool,
            "regional_cool": 0.10 * regional_cool,
            "low_saturation": 0.16 * (1 - saturation),
            "blue_bias": 0.16 * _clamp((blue - red + 0.25) / 0.65),
            "mid_brightness": 0.14 * _clamp(1 - abs(brightness - 0.52) / 0.52),
        },
        "dreamy": {
            "low_contrast": 0.24 * (1 - contrast),
            "lightness": 0.24 * light,
            "soft_saturation": 0.18 * (1 - saturation),
            "center_lightness": 0.12 * _clamp(features.center_brightness_delta + 0.5),
        },
        "soft": {
            "low_saturation": 0.24 * (1 - saturation),
            "lightness": 0.25 * light,
            "low_contrast": 0.16 * (1 - contrast),
            "low_dark_ratio": 0.15 * (1 - dark),
        },
        "moody": {
            "darkness": 0.38 * dark,
            "contrast": 0.24 * contrast,
            "low_brightness": 0.16 * (1 - brightness),
            "cool_or_warm_depth": 0.08 * max(warm, cool),
        },
        "minimal": {
            "low_complexity": 0.30 * gray,
            "low_saturation": 0.24 * (1 - saturation),
            "low_contrast": 0.16 * (1 - contrast),
            "low_text": 0.12 * (1 - text),
        },
        "cozy": {
            "warmth": 0.34 * warm,
            "mid_brightness": 0.22 * _clamp(1 - abs(brightness - 0.52) / 0.52),
            "moderate_saturation": 0.18 * _clamp(1 - abs(saturation - 0.45) / 0.45),
            "low_contrast": 0.12 * (1 - contrast),
        },
        "cinematic": {
            "contrast": 0.30 * contrast,
            "darkness": 0.20 * dark,
            "moderate_saturation": 0.18 * _clamp(1 - abs(saturation - 0.45) / 0.45),
            "color_temperature": 0.12 * max(warm, cool),
        },
        "playful": {
            "saturation": 0.34 * saturation,
            "brightness": 0.22 * brightness,
            "color": 0.18 * (1 - gray),
            "warmth_or_cool": 0.10 * max(warm, cool),
        },
        "edgy": {
            "contrast": 0.30 * contrast,
            "darkness": 0.28 * dark,
            "saturation": 0.18 * saturation,
            "text_or_graphic": 0.10 * text,
        },
        "romantic": {
            "warmth": 0.26 * warm,
            "softness": 0.22 * (1 - contrast),
            "brightness": 0.16 * brightness,
            "color": 0.14 * (1 - gray),
        },
    }


def score_vibe_contributions(features: ImageFeatures) -> dict[str, dict[str, float]]:
    """Return normalized, weighted evidence for every canonical vibe.

    Each contribution is divided by that vibe's maximum possible weighted
    score. The resulting values remain heuristic evidence, not probabilities.
    """
    components = _score_components(features)
    normalized: dict[str, dict[str, float]] = {}
    for name, values in components.items():
        maximum = VIBE_MAX_SCORES[name]
        normalized[name] = {
            feature: round(value / maximum, 4)
            for feature, value in values.items()
        }
    return normalized


def score_vibes(features: ImageFeatures) -> tuple[VibeScore, ...]:
    """Rank canonical vibes by normalized heuristic evidence, not probability."""
    contributions = score_vibe_contributions(features)
    scores = {
        name: _clamp(sum(values.values())) for name, values in contributions.items()
    }
    return tuple(
        sorted(
            (VibeScore(name, round(score, 4)) for name, score in scores.items()),
            key=lambda result: result.score,
            reverse=True,
        )
    )


def select_vibes(
    scores: tuple[VibeScore, ...],
    *,
    threshold: float = DEFAULT_VIBE_THRESHOLD,
    margin: float = DEFAULT_VIBE_MARGIN,
) -> tuple[VibeScore, ...]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if margin < 0:
        raise ValueError("margin must be non-negative")
    if not scores:
        return ()
    winner = scores[0].score
    selected = tuple(
        score
        for score in scores
        if score.score >= threshold and winner - score.score <= margin
    )
    return selected or (scores[0],)


def confidence_score(
    scores: tuple[VibeScore, ...], *, margin_scale: float = CONFIDENCE_MARGIN_SCALE
) -> float:
    """Return a bounded heuristic ranking signal, not a calibrated probability."""
    if not scores:
        return 0.0
    if margin_scale <= 0:
        raise ValueError("margin_scale must be greater than 0")
    winner = scores[0].score
    runner_up = scores[1].score if len(scores) > 1 else 0.0
    margin = _clamp(max(0.0, winner - runner_up) / margin_scale)
    return round(_clamp(0.65 * winner + 0.35 * margin), 4)


def is_confident(
    scores: tuple[VibeScore, ...],
    *,
    min_score: float = MIN_CONFIDENT_SCORE,
    min_margin: float = MIN_CONFIDENT_MARGIN,
) -> bool:
    if not scores:
        return False
    if not 0 <= min_score <= 1:
        raise ValueError("min_score must be between 0 and 1")
    if min_margin < 0:
        raise ValueError("min_margin must be non-negative")
    margin = scores[0].score if len(scores) == 1 else scores[0].score - scores[1].score
    return scores[0].score >= min_score and margin >= min_margin


def assess_confidence(
    scores: tuple[VibeScore, ...],
    *,
    thresholds: ConfidenceThresholds = DEFAULT_CONFIDENCE_THRESHOLDS,
) -> ConfidenceAssessment:
    """Separate raw scores, ranking margin, and user-facing confidence.

    Scores and ranking_signal are heuristic signals, not calibrated probabilities.
    A label is withheld when evidence is weak or the leading candidates are too close.
    All category boundaries are configured in DEFAULT_CONFIDENCE_THRESHOLDS.
    """
    if not scores:
        return ConfidenceAssessment("uncertain", None, 0.0, 0.0, 0.0, "No usable feature evidence was available.")
    winner = scores[0].score
    runner_up = scores[1].score if len(scores) > 1 else 0.0
    margin = round(max(0.0, winner - runner_up), 4)
    signal = confidence_score(scores)
    if winner < thresholds.possible_score:
        return ConfidenceAssessment("uncertain", None, winner, margin, signal, "The strongest heuristic score is below the minimum evidence threshold.")
    if margin < thresholds.possible_margin:
        return ConfidenceAssessment("uncertain", None, winner, margin, signal, "The leading labels are too close to distinguish reliably.")
    if winner >= thresholds.strong_score and margin >= thresholds.strong_margin:
        return ConfidenceAssessment("strong", scores[0].name, winner, margin, signal, "The leading score is strong and clearly separated from alternatives.")
    return ConfidenceAssessment("possible", scores[0].name, winner, margin, signal, "There is a usable leading signal, but it is not strong enough for a strong label.")


def classify(features: ImageFeatures) -> VibeScore:
    """Return the top-ranked raw heuristic score, not a guaranteed label."""
    return score_vibes(features)[0]


def classify_label(features: ImageFeatures) -> str | None:
    """Return a label only when heuristic evidence clears abstention thresholds."""
    return assess_confidence(score_vibes(features)).label


CANONICAL_VIBES = tuple(item.value for item in Vibe)
VIBES = CANONICAL_VIBES
