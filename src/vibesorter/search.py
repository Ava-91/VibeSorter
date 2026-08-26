from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .cache import AnalysisCache
from .features import ImageFeatures
from .pipeline import AnalysisResult
from .vibes import VibeScore


@dataclass(frozen=True, slots=True)
class ImageQuery:
    """Pure search criteria shared by the CLI and future interfaces."""

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


def _matches(result: AnalysisResult, query: ImageQuery) -> bool:
    features = result.features
    if query.vibe is not None and result.best.name != query.vibe:
        return False
    if result.best.score < query.min_score:
        return False
    if features.text_likelihood > query.max_text_likelihood:
        return False
    path_text = str(result.path).casefold()
    if query.path_contains is not None and query.path_contains.casefold() not in path_text:
        return False
    dimensions = (
        (features.brightness, query.min_brightness, query.max_brightness),
        (features.saturation, query.min_saturation, query.max_saturation),
        (features.contrast, query.min_contrast, query.max_contrast),
    )
    for value, minimum, maximum in dimensions:
        if minimum is not None and value < minimum:
            return False
        if maximum is not None and value > maximum:
            return False
    return True


def search_cache(cache: AnalysisCache, query: ImageQuery) -> tuple[AnalysisResult, ...]:
    """Search valid cached results only; this function never analyzes images."""
    matches: list[AnalysisResult] = []
    for path, features, scores in cache.entries():
        result = AnalysisResult(path, features, scores[0], scores, cached=True)
        if _matches(result, query):
            matches.append(result)
    matches.sort(key=lambda result: (-result.best.score, str(result.path).casefold()))
    if query.limit is not None:
        return tuple(matches[:query.limit])
    return tuple(matches)
