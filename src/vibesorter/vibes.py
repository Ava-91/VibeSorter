from __future__ import annotations

from dataclasses import dataclass

from .features import ImageFeatures

VIBES = ("Retro Blue", "Red / Warm", "Green & Black", "Black & White", "Soft / Pastel", "Dark / Moody", "Bright / Colorful", "Neutral / Photo Dump")
MIN_CONFIDENT_SCORE = 0.60
MIN_CONFIDENT_MARGIN = 0.08
CONFIDENCE_MARGIN_SCALE = 0.25
DEFAULT_VIBE_THRESHOLD = 0.45
DEFAULT_VIBE_MARGIN = 0.10

@dataclass(frozen=True, slots=True)
class VibeScore:
    name: str
    score: float

def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))

def _score_components(features: ImageFeatures) -> dict[str, dict[str, float]]:
    """Return each vibe's weighted feature contributions before sorting."""
    r, g, b = (value / 255.0 for value in features.average_rgb)
    brightness, saturation, contrast = features.brightness, features.saturation, features.contrast
    gray, dark, light = features.grayscale_ratio, features.dark_ratio, features.light_ratio
    center_delta = features.center_brightness_delta
    regional_cool = max((region.cool_ratio for region in features.regions), default=features.cool_ratio)
    regional_saturation = max((region.saturation for region in features.regions), default=saturation)
    components = {
        "Retro Blue": {
            "cool_ratio": 0.30 * features.cool_ratio,
            "regional_cool": 0.08 * regional_cool,
            "low_saturation": 0.16 * (1 - saturation),
            "blue_shift": 0.18 * _clamp((b-r+0.25)/0.65),
            "regional_saturation": 0.04 * regional_saturation,
            "mid_brightness": 0.16 * _clamp(1-abs(brightness-0.52)/0.52),
            "center_darkness": 0.12 * _clamp(-center_delta+0.5),
        },
        "Red / Warm": {
            "warm_ratio": 0.46 * features.warm_ratio,
            "warm_color_shift": 0.23 * _clamp((r-b+0.20)/0.70),
            "saturation": 0.13 * saturation,
            "low_dark_ratio": 0.08 * _clamp(1-dark),
            "center_brightness": 0.10 * _clamp(center_delta+0.5),
        },
        "Green & Black": {
            "green_red_shift": 0.40 * _clamp((g-r+0.15)/0.55),
            "dark_ratio": 0.28 * dark,
            "saturation": 0.15 * saturation,
            "green_blue_shift": 0.09 * _clamp((g-b+0.15)/0.55),
            "center_darkness": 0.08 * _clamp(-center_delta+0.5),
        },
        "Black & White": {
            "grayscale_ratio": 0.58 * gray,
            "contrast": 0.22 * contrast,
            "dark_or_light": 0.12 * _clamp(dark+light),
            "center_separation": 0.08 * _clamp(abs(center_delta)+0.25),
        },
        "Soft / Pastel": {
            "low_saturation": 0.20 * (1-saturation),
            "light_ratio": 0.32 * light,
            "low_contrast": 0.10 * _clamp(1-contrast),
            "brightness": 0.24 * brightness,
            "center_brightness": 0.10 * _clamp(center_delta+0.5),
            "low_dark_ratio": 0.14 * _clamp(1-dark),
        },
        "Dark / Moody": {
            "dark_ratio": 0.42 * dark,
            "contrast": 0.23 * contrast,
            "saturation": 0.15 * saturation,
            "low_brightness": 0.10 * _clamp(1-brightness),
            "center_darkness": 0.10 * _clamp(-center_delta+0.5),
        },
        "Bright / Colorful": {
            "light_ratio": 0.34 * light,
            "saturation": 0.30 * saturation,
            "brightness": 0.18 * brightness,
            "non_grayscale": 0.10 * _clamp(1-gray),
            "center_brightness": 0.08 * _clamp(center_delta+0.5),
        },
    }
    components["Soft / Pastel"]["darkness_penalty"] = -_pastel_darkness_penalty(features)

    existing_scores = {
        name: _clamp(sum(values.values())) for name, values in components.items()
    }
    strongest_aesthetic = max(existing_scores.values(), default=0.0)
    components["Neutral / Photo Dump"] = {
        "absence_of_strong_aesthetic": _clamp(
            (1.0 - strongest_aesthetic) * (0.65 + 0.35 * contrast)
        ),
    }
    return components

def _pastel_darkness_penalty(features: ImageFeatures) -> float:
    """Penalize Soft / Pastel when an image is substantially dark-heavy."""
    return 0.28 * _clamp((features.dark_ratio - 0.22) / 0.45)

def score_vibe_contributions(features: ImageFeatures) -> dict[str, dict[str, float]]:
    """Return weighted feature contributions for every vibe.

    The contribution values sum to the corresponding raw vibe score. This
    mirrors ``score_vibes`` without changing its classification behavior.
    """
    return {
        name: {feature: round(value, 4) for feature, value in components.items()}
        for name, components in _score_components(features).items()
    }

def score_vibes(features: ImageFeatures) -> tuple[VibeScore, ...]:
    """Score overlapping atmospheric categories from global and spatial features."""
    components = _score_components(features)
    scores = {name: _clamp(sum(values.values())) for name, values in components.items()}
    return tuple(sorted((VibeScore(name, round(score, 4)) for name, score in scores.items()), key=lambda result: result.score, reverse=True))

def select_vibes(scores: tuple[VibeScore, ...], *, threshold: float = DEFAULT_VIBE_THRESHOLD, margin: float = DEFAULT_VIBE_MARGIN) -> tuple[VibeScore, ...]:
    """Return all meaningful vibes while retaining the strongest winner."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if margin < 0:
        raise ValueError("margin must be non-negative")
    if not scores:
        return ()
    winner = scores[0].score
    selected = tuple(score for score in scores if score.score >= threshold and winner - score.score <= margin)
    return selected or (scores[0],)

def confidence_score(scores: tuple[VibeScore, ...], *, margin_scale: float = CONFIDENCE_MARGIN_SCALE) -> float:
    if not scores: return 0.0
    if margin_scale <= 0: raise ValueError("margin_scale must be greater than 0")
    winner, runner_up = scores[0].score, scores[1].score if len(scores) > 1 else 0.0
    return round(_clamp(0.65 * winner + 0.35 * _clamp(max(0.0, winner-runner_up)/margin_scale)), 4)

def is_confident(scores: tuple[VibeScore, ...], *, min_score: float = MIN_CONFIDENT_SCORE, min_margin: float = MIN_CONFIDENT_MARGIN) -> bool:
    if not scores: return False
    if not 0 <= min_score <= 1: raise ValueError("min_score must be between 0 and 1")
    if min_margin < 0: raise ValueError("min_margin must be non-negative")
    margin = scores[0].score if len(scores) == 1 else scores[0].score - scores[1].score
    return scores[0].score >= min_score and margin >= min_margin

def classify(features: ImageFeatures) -> VibeScore:
    return score_vibes(features)[0]
