from __future__ import annotations

from .features import ImageFeatures
from .profile import AttributeValue, ImageProfile
from .vibes import score_vibes


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _confidence(value: float) -> float:
    return round(_clamp(value), 4)


def _color_values(features: ImageFeatures) -> tuple[AttributeValue, ...]:
    candidates: list[AttributeValue] = []
    for sample in features.colors:
        rgb, proportion = sample.rgb, sample.proportion
        r, g, b = (component / 255 for component in rgb)
        maximum = max(r, g, b)
        minimum = min(r, g, b)
        if maximum - minimum < 0.08:
            continue
        if r == maximum:
            value = "red" if g < r * 0.8 and b < r * 0.8 else "orange" if g >= r * 0.55 and b < g * 0.75 else "pink"
        elif g == maximum:
            value = "green" if r < g * 0.8 and b < g * 0.8 else "yellow"
        else:
            value = "blue" if r < b * 0.8 and g < b * 0.9 else "purple"
        confidence = proportion * _clamp(1.0 + (maximum - minimum))
        candidates.append(AttributeValue(value, _confidence(confidence), "heuristic"))

    best: dict[str, AttributeValue] = {}
    for candidate in candidates:
        previous = best.get(candidate.value)
        if previous is None or candidate.confidence > previous.confidence:
            best[candidate.value] = candidate
    selected = [item for item in best.values() if item.confidence >= 0.12]
    selected.sort(key=lambda item: item.confidence, reverse=True)
    return tuple(selected[:3]) or (
        AttributeValue("neutral", _confidence(features.grayscale_ratio), "heuristic"),
    )


def _media_type(features: ImageFeatures) -> AttributeValue:
    text = features.text_likelihood
    gray = features.grayscale_ratio
    contrast = features.contrast
    if text >= 0.82 and gray >= 0.55:
        return AttributeValue("screenshot", _confidence(0.65 + 0.35 * text), "heuristic")
    if text >= 0.70:
        return AttributeValue("graphic", _confidence(0.55 + 0.35 * text), "heuristic")
    confidence = _clamp(0.55 + 0.25 * (1 - text) + 0.20 * (1 - contrast))
    return AttributeValue("photograph", _confidence(confidence), "heuristic")


def _temperature(features: ImageFeatures) -> AttributeValue:
    warm, cool = features.warm_ratio, features.cool_ratio
    if abs(warm - cool) < 0.08:
        return AttributeValue(
            "neutral", _confidence(0.60 + 0.30 * (1 - abs(warm - cool) / 0.08)), "heuristic"
        )
    value = "warm" if warm > cool else "cool"
    confidence = 0.55 + 0.45 * _clamp(abs(warm - cool) / 0.6)
    return AttributeValue(value, _confidence(confidence), "heuristic")


def _saturation(features: ImageFeatures) -> AttributeValue:
    if features.saturation >= 0.62:
        value, confidence = "vibrant", 0.55 + 0.45 * features.saturation
    elif features.saturation >= 0.28:
        value, confidence = "muted", 0.60 + 0.25 * (1 - abs(features.saturation - 0.45) / 0.28)
    else:
        value, confidence = "desaturated", 0.60 + 0.40 * (1 - features.saturation / 0.28)
    return AttributeValue(value, _confidence(confidence), "heuristic")


def _brightness(features: ImageFeatures) -> AttributeValue:
    if features.brightness >= 0.68:
        value, confidence = "bright", 0.60 + 0.40 * features.brightness
    elif features.brightness <= 0.34:
        value, confidence = "dark", 0.60 + 0.40 * (1 - features.brightness)
    else:
        value, confidence = "mid", 0.62 + 0.25 * (1 - abs(features.brightness - 0.51) / 0.17)
    return AttributeValue(value, _confidence(confidence), "heuristic")


def _vibes(features: ImageFeatures) -> tuple[AttributeValue, ...]:
    scores = score_vibes(features)
    if not scores:
        return ()
    winner = scores[0].score
    return tuple(
        AttributeValue(score.name, score.score, "heuristic")
        for score in scores
        if score.score >= 0.45 and winner - score.score <= 0.15
    )


def classify_profile(features: ImageFeatures) -> ImageProfile:
    """Return an independent, multi-dimensional semantic profile."""
    return ImageProfile(
        media_type=_media_type(features),
        colors=_color_values(features),
        temperature=_temperature(features),
        saturation=_saturation(features),
        brightness=_brightness(features),
        vibes=_vibes(features),
    )
