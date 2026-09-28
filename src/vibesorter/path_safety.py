from __future__ import annotations

import os
from pathlib import Path


def canonical_path(path: str | Path) -> Path:
    """Return a normalized absolute path suitable for conflict comparisons."""
    resolved = Path(path).expanduser().resolve(strict=False)
    return Path(os.path.normcase(str(resolved)))


def same_path(left: str | Path, right: str | Path) -> bool:
    return canonical_path(left) == canonical_path(right)
