from __future__ import annotations

from dataclasses import dataclass, field

from .cache import AnalysisCache
from .pipeline import AnalysisResult
from .profile import ImageProfile


@dataclass(frozen=True, slots=True)
class ImageQuery:
    """Structured image search; values within one family are ORed, families ANDed."""

    vibe: str | None = None
    min_score: float = 0.0
    max_text_likelihood: float = 1.0
    path_contains: str | None = None
    min_brightness: float | None = None
    max_brightness: float | None = None
    min_saturation: float | None = None
    max_saturation: float | None = None
    min_contrast: float | None = None
    max_contrast: float | None = None
    limit: int | None = None
    include_secondary_vibes: bool = True
    media_type: str | None = None
    colors: tuple[str, ...] = field(default_factory=tuple)
    temperature: str | None = None
    saturation: str | None = None
    brightness: str | None = None
    vibes: tuple[str, ...] = field(default_factory=tuple)


def _has(values: tuple[str, ...], selected: tuple[str, ...]) -> bool:
    return not selected or any(value in selected for value in values)


def _matches_profile(profile: ImageProfile | None, query: ImageQuery) -> bool:
    if profile is None:
        return not any((query.media_type, query.temperature, query.saturation, query.brightness, query.colors, query.vibes))
    if query.media_type and (profile.media_type is None or profile.media_type.value != query.media_type):
        return False
    if query.temperature and (profile.temperature is None or profile.temperature.value != query.temperature):
        return False
    if query.saturation and (profile.saturation is None or profile.saturation.value != query.saturation):
        return False
    if query.brightness and (profile.brightness is None or profile.brightness.value != query.brightness):
        return False
    colors = tuple(item.value for item in profile.colors)
    vibes = tuple(item.value for item in profile.vibes)
    return _has(colors, query.colors) and _has(vibes, query.vibes)


def _matches(result: AnalysisResult, query: ImageQuery, profile: ImageProfile | None = None) -> bool:
    features = result.features
    if query.vibe is not None:
        matching = result.scores if query.include_secondary_vibes else (result.best,)
        if not any(score.name == query.vibe and score.score >= query.min_score for score in matching):
            return False
    elif result.best.score < query.min_score:
        return False
    if features.text_likelihood > query.max_text_likelihood:
        return False
    path_text = str(result.path).casefold()
    if query.path_contains is not None and query.path_contains.casefold() not in path_text:
        return False
    for value, minimum, maximum in (
        (features.brightness, query.min_brightness, query.max_brightness),
        (features.saturation, query.min_saturation, query.max_saturation),
        (features.contrast, query.min_contrast, query.max_contrast),
    ):
        if minimum is not None and value < minimum:
            return False
        if maximum is not None and value > maximum:
            return False
    return _matches_profile(profile, query)


def search_cache(cache: AnalysisCache, query: ImageQuery) -> tuple[AnalysisResult, ...]:
    """Search valid cached results without touching source image pixels."""
    matches = []
    for path, features, scores in cache.entries():
        result = AnalysisResult(path, features, scores[0], scores, cached=True)
        if _matches(result, query, cache.get_profile(path)):
            matches.append(result)
    matches.sort(key=lambda result: (-result.best.score, str(result.path).casefold()))
    return tuple(matches[:query.limit]) if query.limit is not None else tuple(matches)
