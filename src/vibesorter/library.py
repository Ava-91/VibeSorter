from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from .cache import AnalysisCache
from .pipeline import AnalysisResult, analyze_image
from .scanner import find_images

@dataclass(frozen=True, slots=True)
class LibraryAnalysisStats:
    total: int; cached: int; analyzed: int; skipped: int; removed_from_cache: int
    def to_dict(self) -> dict[str, int]: return asdict(self)

def analyze_library(folder: str | Path, *, recursive: bool = False, cache_path: str | Path | None = None, on_progress: Callable[[int, int, Path, bool], None] | None = None) -> Iterator[AnalysisResult]:
    """Analyze a library while persisting results in the local SQLite index."""
    root = Path(folder).expanduser(); cache = AnalysisCache(cache_path or root / '.vibesorter' / 'analysis.db')
    images = find_images(root, recursive=recursive); cache.remove_missing(); total = len(images)
    for index, image in enumerate(images, start=1):
        result = analyze_image(image, cache=cache)
        if on_progress is not None: on_progress(index, total, image, result.cached)
        yield result
    cache.save(); cache.close()

def analyze_library_stats(folder: str | Path, *, recursive: bool = False) -> LibraryAnalysisStats:
    root = Path(folder).expanduser(); cache = AnalysisCache(root / '.vibesorter' / 'analysis.db'); removed = cache.remove_missing(); images = find_images(root, recursive=recursive)
    results = [analyze_image(image, cache=cache) for image in images]; cache.save(); cache.close(); cached = sum(result.cached for result in results)
    return LibraryAnalysisStats(len(results), cached, len(results)-cached, 0, removed)
