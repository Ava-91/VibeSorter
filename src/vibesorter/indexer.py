from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .cache import AnalysisCache
from .pipeline import analyze_image
from .scanner import find_images


def index_folder(
    folder: str | Path,
    *,
    recursive: bool = True,
    workers: int = 8,
) -> dict[str, int]:
    """Incrementally analyze a folder into its local SQLite cache."""
    if workers < 1:
        raise ValueError("workers must be at least 1")

    root = Path(folder).expanduser()
    images = find_images(root, recursive=recursive)
    cache_path = root / ".vibesorter" / "analysis.db"

    analyzed = 0
    reused = 0
    skipped = 0

    with AnalysisCache(cache_path) as cache:
        pending: list[Path] = []
        for image in images:
            if cache.get(image) is None:
                pending.append(image)
            else:
                reused += 1

        def analyze(path: Path):
            try:
                return path, analyze_image(path), None
            except Exception as exc:  # pragma: no cover - exact decoder errors vary by image
                return path, None, exc

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for path, result, error in executor.map(analyze, pending):
                if error is not None:
                    skipped += 1
                    continue
                cache.set(path, result.features, result.scores)
                analyzed += 1

        removed = cache.remove_missing()
        cache.save()

    return {
        "total": len(images),
        "analyzed": analyzed,
        "reused": reused,
        "skipped": skipped,
        "removed": removed,
        "database": str(cache_path),
    }
