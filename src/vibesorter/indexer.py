from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .verified_cache import VerifiedAnalysisCache
from .classifier import classify_profile
from .pipeline import analyze_image
from .scanner import find_images

ProgressCallback = Callable[[dict[str, int | str]], None]


def index_folder(
    folder: str | Path,
    *,
    recursive: bool = True,
    workers: int = 8,
    progress: ProgressCallback | None = None,
) -> dict[str, int | str]:
    """Incrementally analyze a folder into its local SQLite cache."""
    if workers < 1:
        raise ValueError("workers must be at least 1")

    root = Path(folder).expanduser()
    images = find_images(root, recursive=recursive)
    cache_path = root / ".vibesorter" / "analysis.db"

    analyzed = 0
    reused = 0
    skipped = 0

    if progress:
        progress({"phase": "scan", "total": len(images)})

    with VerifiedAnalysisCache(cache_path) as cache:
        pending: list[Path] = []
        for image in images:
            if cache.get_verified(image) is None:
                pending.append(image)
            else:
                reused += 1

        if progress:
            progress({"phase": "analyze", "total": len(images), "pending": len(pending), "reused": reused})

        def analyze(path: Path):
            try:
                return path, analyze_image(path), None
            except Exception as exc:  # pragma: no cover - exact decoder errors vary by image
                return path, None, exc

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for path, result, error in executor.map(analyze, pending):
                if error is not None:
                    skipped += 1
                    if progress:
                        progress({"phase": "analyze", "completed": analyzed + skipped, "total": len(images), "skipped": skipped})
                    continue
                cache.set(path, result.features, result.scores)
                cache.set_profile(path, classify_profile(result.features))
                analyzed += 1
                if progress:
                    progress({"phase": "analyze", "completed": analyzed + skipped, "total": len(images), "skipped": skipped})

        removed = cache.remove_missing()
        cache.save()

    result = {
        "total": len(images),
        "analyzed": analyzed,
        "reused": reused,
        "skipped": skipped,
        "removed": removed,
        "database": str(cache_path),
    }
    if progress:
        progress({"phase": "complete", "total": len(images), "analyzed": analyzed, "reused": reused, "skipped": skipped, "removed": removed})
    return result
