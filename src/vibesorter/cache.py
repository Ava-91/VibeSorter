"""Persistent analysis cache compatibility layer.

The public ``AnalysisCache`` API now uses SQLite. Legacy callers that still
refer to ``analysis.json`` are transparently redirected to the sibling
``analysis.db`` file, where the JSON file is used only as migration input.
"""

from pathlib import Path

from .sqlite_cache import DEFAULT_SQLITE_PATH, SCHEMA_VERSION, SQLiteAnalysisCache


class AnalysisCache(SQLiteAnalysisCache):
    def __init__(self, path: str | Path = DEFAULT_SQLITE_PATH) -> None:
        requested = Path(path).expanduser()
        if requested.suffix.lower() == ".json":
            sqlite_path = requested.with_suffix(".db")
        else:
            sqlite_path = requested
        super().__init__(sqlite_path)


DEFAULT_CACHE_PATH = DEFAULT_SQLITE_PATH
__all__ = ["AnalysisCache", "DEFAULT_CACHE_PATH", "SCHEMA_VERSION"]
