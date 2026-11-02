from __future__ import annotations

import math
import time
from collections.abc import Callable
from pathlib import Path
from threading import Event

from .indexer import index_folder
from .scanner import find_images

MonitorCallback = Callable[[dict[str, int | str]], None]


def _snapshot(folder: str | Path) -> tuple[tuple[str, int, int], ...]:
    """Capture image paths and file identities without reading image contents."""
    return tuple(
        (str(path), stat.st_size, stat.st_mtime_ns)
        for path in find_images(folder)
        for stat in (path.stat(),)
    )


def monitor_folder(
    folder: str | Path,
    *,
    interval: float = 60.0,
    workers: int = 8,
    on_update: MonitorCallback | None = None,
    stop_event: Event | None = None,
) -> dict[str, int | str]:
    """Keep a folder's local analysis cache incrementally synchronized.

    This is an explicit foreground monitor, not a background service. It polls
    image metadata at a conservative interval and only invokes the indexer
    after a path, size, or modification-time change is detected. It never
    moves, renames, deletes, or edits source images.
    """
    if not math.isfinite(interval) or interval < 5:
        raise ValueError("monitor interval must be a finite number of at least 5 seconds")
    if workers < 1:
        raise ValueError("workers must be at least 1")

    root = Path(folder).expanduser()
    previous = _snapshot(root)
    result = index_folder(root, workers=workers)
    if on_update is not None:
        on_update(result)

    while stop_event is None or not stop_event.is_set():
        if stop_event is not None:
            if stop_event.wait(interval):
                break
        else:
            time.sleep(interval)

        current = _snapshot(root)
        if current == previous:
            continue

        # Keep the pre-index snapshot. If a file changes while indexing, the
        # next poll will see that newer identity and retry the incremental pass.
        previous = current
        result = index_folder(root, workers=workers)
        if on_update is not None:
            on_update(result)

    return result
