"""Persistent analysis cache compatibility layer.

The public ``AnalysisCache`` API now uses SQLite. The implementation lives in
``sqlite_cache`` so callers retain the same get/set/entries/save interface.
"""

from .sqlite_cache import DEFAULT_SQLITE_PATH as DEFAULT_CACHE_PATH
from .sqlite_cache import SCHEMA_VERSION
from .sqlite_cache import SQLiteAnalysisCache

AnalysisCache = SQLiteAnalysisCache

__all__ = ["AnalysisCache", "DEFAULT_CACHE_PATH", "SCHEMA_VERSION"]
