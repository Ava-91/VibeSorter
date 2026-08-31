from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .cache import AnalysisCache
from .features import ImageFeatures, extract_features
from .scanner import find_images
from .vibes import VibeScore, score_vibes, select_vibes

@dataclass(frozen=True, slots=True)
class AnalysisResult:
    path: Path
    features: ImageFeatures
    best: VibeScore
    scores: tuple[VibeScore, ...]
    cached: bool = False
    @property
    def vibes(self) -> tuple[VibeScore, ...]:
        return select_vibes(self.scores)

def analyze_image(path: Path, *, cache: AnalysisCache | None = None) -> AnalysisResult:
    image_path = Path(path).expanduser()
    if cache is not None:
        cached = cache.get(image_path)
        if cached is not None:
            features, scores = cached
            return AnalysisResult(image_path, features, scores[0], scores, cached=True)
    features = extract_features(image_path); scores = score_vibes(features)
    if cache is not None: cache.set(image_path, features, scores)
    return AnalysisResult(image_path, features, scores[0], scores)

def analyze_folder(folder: Path, *, recursive: bool = False, on_progress: Callable[[int, int, Path], None] | None = None, cache: AnalysisCache | None = None) -> Iterator[AnalysisResult]:
    images = find_images(folder, recursive=recursive); total = len(images)
    for index, path in enumerate(images, start=1):
        result = analyze_image(path, cache=cache)
        if on_progress is not None: on_progress(index, total, path)
        yield result
    if cache is not None: cache.save()
