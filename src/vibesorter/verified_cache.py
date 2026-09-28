from __future__ import annotations

import hashlib
from pathlib import Path

from .cache import AnalysisCache


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class VerifiedAnalysisCache(AnalysisCache):
    """Analysis cache that adds a content digest to stat-based identity checks."""

    def __init__(self, path: str | Path):
        super().__init__(path)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS content_identity "
            "(path TEXT PRIMARY KEY, digest TEXT NOT NULL)"
        )
        self.connection.commit()

    def get_verified(self, path: str | Path):
        result = super().get(path)
        if result is None:
            return None
        image_path = Path(path).expanduser()
        try:
            digest = _digest(image_path)
        except OSError:
            return None
        row = self.connection.execute(
            "SELECT digest FROM content_identity WHERE path=?", (str(image_path),)
        ).fetchone()
        if row is None or row[0] != digest:
            return None
        return result

    def set(self, path, features, scores):
        super().set(path, features, scores)
        image_path = Path(path).expanduser()
        try:
            digest = _digest(image_path)
        except OSError:
            self.connection.execute("DELETE FROM content_identity WHERE path=?", (str(image_path),))
            return
        self.connection.execute(
            "INSERT INTO content_identity(path,digest) VALUES(?,?) "
            "ON CONFLICT(path) DO UPDATE SET digest=excluded.digest",
            (str(image_path), digest),
        )

    def remove_missing(self) -> int:
        removed = super().remove_missing()
        self.connection.execute(
            "DELETE FROM content_identity WHERE path NOT IN (SELECT path FROM images)"
        )
        return removed
