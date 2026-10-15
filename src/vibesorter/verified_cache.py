from __future__ import annotations

import hashlib
from pathlib import Path
from collections.abc import Iterable

from .cache import AnalysisCache


def _digest(path: Path) -> str:
    """Hash a file using the stdlib's buffered native implementation."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class VerifiedAnalysisCache(AnalysisCache):
    """Analysis cache that adds a content digest to stat-based identity checks."""

    def __init__(self, path: str | Path):
        super().__init__(path)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS content_identity "
            "(path TEXT PRIMARY KEY, digest TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TEMP TABLE IF NOT EXISTS scan_candidates (path TEXT PRIMARY KEY)"
        )
        self.connection.commit()

    def get_verified_many(self, paths: Iterable[str | Path]) -> set[Path]:
        """Verify a scan's cache candidates with one SQLite join and content hashes."""
        candidates = tuple(dict.fromkeys(Path(path).expanduser() for path in paths))
        if not candidates:
            return set()

        self.connection.execute("DELETE FROM scan_candidates")
        self.connection.executemany(
            "INSERT OR IGNORE INTO scan_candidates(path) VALUES(?)",
            ((str(path),) for path in candidates),
        )
        rows = self.connection.execute(
            "SELECT i.path, i.size, i.mtime_ns, c.digest "
            "FROM scan_candidates AS s "
            "JOIN images AS i ON i.path = s.path "
            "JOIN content_identity AS c ON c.path = i.path"
        ).fetchall()

        verified: set[Path] = set()
        for raw_path, cached_size, cached_mtime, cached_digest in rows:
            image_path = Path(raw_path).expanduser()
            try:
                stat = image_path.stat()
            except OSError:
                continue
            # Preserve the strict stat + digest contract: files whose metadata
            # changed are reanalyzed, even if their bytes happen to match.
            if (stat.st_size, stat.st_mtime_ns) != (cached_size, cached_mtime):
                continue
            try:
                if _digest(image_path) == cached_digest:
                    verified.add(image_path)
            except OSError:
                continue
        return verified

    def get_verified(self, path: str | Path):
        image_path = Path(path).expanduser()
        if image_path not in self.get_verified_many((image_path,)):
            return None
        return super().get(image_path)

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

    def remove(self, path: str | Path) -> None:
        """Remove stale analysis, profile, and digest rows for a failed image."""
        image_path = Path(path).expanduser()
        self.connection.execute("DELETE FROM images WHERE path=?", (str(image_path),))
        self.connection.execute("DELETE FROM content_identity WHERE path=?", (str(image_path),))

    def remove_missing(self) -> int:
        removed = super().remove_missing()
        self.connection.execute(
            "DELETE FROM content_identity WHERE path NOT IN (SELECT path FROM images)"
        )
        return removed
