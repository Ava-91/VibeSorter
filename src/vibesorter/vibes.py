from __future__ import annotations

from dataclasses import dataclass

from .features import ImageFeatures

VIBES = ("Retro Blue", "Red / Warm", "Green & Black", "Black & White", "Soft / Pastel", "Dark / Moody", "Bright / Colorful")
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

def score_vibes(features: ImageFeatures) -> tuple[VibeScore, ...]:
    """Score overlapping atmospheric categories from global and spatial features."""
    r, g, b = (value / 255.0 for value in features.average_rgb)
    brightness, saturation, contrast = features.brightness, features.saturation, features.contrast
    gray, dark, light = features.grayscale_ratio, features.dark_ratio, features.light_ratio
    center_delta = features.center_brightness_delta
    scores = {
        "Retro Blue": _clamp(0.34 * features.cool_ratio + 0.20 * (1 - saturation) + 0.18 * _clamp((b-r+0.25)/0.65) + 0.16 * _clamp(1-abs(brightness-0.52)/0.52) + 0.12 * _clamp(-center_delta+0.5)),
        "Red / Warm": _clamp(0.46 * features.warm_ratio + 0.23 * _clamp((r-b+0.20)/0.70) + 0.13 * saturation + 0.08 * _clamp(1-dark) + 0.10 * _clamp(center_delta+0.5)),
        "Green & Black": _clamp(0.40 * _clamp((g-r+0.15)/0.55) + 0.28 * dark + 0.15 * saturation + 0.09 * _clamp((g-b+0.15)/0.55) + 0.08 * _clamp(-center_delta+0.5)),
        "Black & White": _clamp(0.58 * gray + 0.22 * contrast + 0.12 * _clamp(dark+light) + 0.08 * _clamp(abs(center_delta)+0.25)),
        "Soft / Pastel": _clamp(0.30 * (1-saturation) + 0.28 * light + 0.18 * _clamp(1-contrast) + 0.14 * brightness + 0.10 * _clamp(center_delta+0.5)),
        "Dark / Moody": _clamp(0.42 * dark + 0.23 * contrast + 0.15 * saturation + 0.10 * _clamp(1-brightness) + 0.10 * _clamp(-center_delta+0.5)),
        "Bright / Colorful": _clamp(0.34 * light + 0.30 * saturation + 0.18 * brightness + 0.10 * _clamp(1-gray) + 0.08 * _clamp(center_delta+0.5)),
    }
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
