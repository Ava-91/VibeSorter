from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .cache import AnalysisCache
from .pipeline import AnalysisResult, analyze_image
from .scanner import find_images


def analyze_library(
    folder: str | Path,
    *,
    recursive: bool = False,
    cache_path: str | Path | None = None,
) -> Iterator[AnalysisResult]:
    """Analyze a library while persisting results in a local JSON index."""
    root = Path(folder).expanduser()
    cache = AnalysisCache(cache_path or root / ".vibesorter" / "analysis.json")
    for image in find_images(root, recursive=recursive):
        yield analyze_image(image, cache=cache)
    cache.save()
