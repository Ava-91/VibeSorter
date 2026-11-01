from __future__ import annotations

import hashlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .classifier import classify_profile
from .pipeline import analyze_image
from .scanner import find_images
from .verified_cache import VerifiedAnalysisCache

MAX_SNAPSHOT_BYTES = 256 * 1024 * 1024

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
        verified_paths = cache.get_verified_many(images)
        reused = len(verified_paths)
        pending = [image for image in images if image.expanduser() not in verified_paths]

        if progress:
            progress({"phase": "analyze", "total": len(images), "pending": len(pending), "reused": reused})

        def analyze(path: Path):
            try:
                # Analyze an immutable byte snapshot. Hashing the path and then
                # reopening it for decoding leaves a TOCTOU window where the
                # digest and extracted features can describe different bytes.
                stat = path.stat()
                if stat.st_size > MAX_SNAPSHOT_BYTES:
                    raise ValueError(f"Image file exceeds {MAX_SNAPSHOT_BYTES:,}-byte limit: {path}")
                image_bytes = path.read_bytes()
                identity = (stat.st_size, stat.st_mtime_ns)
                digest = hashlib.sha256(image_bytes).hexdigest()
                return path, analyze_image(path, image_bytes=image_bytes), None, identity, digest
            except Exception as exc:  # pragma: no cover - exact decoder errors vary by image
                return path, None, exc, None, None

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for path, result, error, identity, digest in executor.map(analyze, pending):
                if error is not None:
                    # A changed image that no longer decodes must not keep its old cached result.
                    cache.remove(path)
                    skipped += 1
                    if progress:
                        progress({"phase": "analyze", "completed": analyzed + skipped, "total": len(images), "skipped": skipped})
                    continue
                if not cache.set(path, result.features, result.scores, expected_identity=identity, expected_digest=digest):
                    skipped += 1
                    if progress:
                        progress({"phase": "analyze", "completed": analyzed + skipped, "total": len(images), "skipped": skipped})
                    continue
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
