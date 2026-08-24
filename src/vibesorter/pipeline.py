from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .features import extract_features
from .scanner import discover_images
from .vibes import VibeScore, score_vibes


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    path: Path
    best: VibeScore
    scores: tuple[VibeScore, ...]


def analyze_image(path: Path) -> AnalysisResult:
    """Analyze one image locally and return its complete vibe ranking."""
    features = extract_features(path)
    scores = score_vibes(features)
    return AnalysisResult(path=path, best=scores[0], scores=scores)


def analyze_folder(
    folder: Path,
    *,
    recursive: bool = False,
    on_progress: Callable[[int, int, Path], None] | None = None,
) -> Iterator[AnalysisResult]:
    """Analyze images one at a time so large folders stay memory-friendly."""
    images = discover_images(folder, recursive=recursive)
    total = len(images)

    for index, path in enumerate(images, start=1):
        result = analyze_image(path)
        if on_progress:
            on_progress(index, total, path)
        yield result
