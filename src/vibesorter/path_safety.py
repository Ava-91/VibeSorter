from __future__ import annotations

import os
from pathlib import Path


def canonical_path(path: str | Path) -> Path:
    """Return a normalized absolute path suitable for conflict comparisons."""
    resolved = Path(path).expanduser().resolve(strict=False)
    return Path(os.path.normcase(str(resolved)))


def same_path(left: str | Path, right: str | Path) -> bool:
    return canonical_path(left) == canonical_path(right)


def is_within(path: str | Path, root: str | Path, *, allow_root: bool = True) -> bool:
    """Return whether a canonical path is contained by a canonical root."""
    candidate = canonical_path(path)
    parent = canonical_path(root)
    return (allow_root and candidate == parent) or parent in candidate.parents


def has_traversal(path: str | Path) -> bool:
    """Reject explicit parent traversal instead of relying on normalization."""
    return ".." in Path(path).parts
