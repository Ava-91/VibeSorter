import json
import sqlite3
from pathlib import Path

from vibesorter.browser.server import _query_rows


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, scores TEXT)"
        )
        rows = [
            ("/photos/Z.png", 300, 30, json.dumps([{"name": "Retro Blue", "score": 0.7}])),
            ("/photos/a.png", 100, 20, json.dumps([{"name": "Dark / Moody", "score": 0.9}])),
            ("/photos/M.png", 200, 10, json.dumps([{"name": "Soft / Pastel", "score": 0.5}])),
        ]
        conn.executemany("INSERT INTO images VALUES (?, ?, ?, ?)", rows)
        conn.commit()
    return db


def _paths(db: Path, **params: list[str]) -> list[str]:
    rows, _ = _query_rows(db, params, limit=20, offset=0)
    return [row["path"] for row in rows]


def test_browser_sorts_by_path(tmp_path: Path):
    db = _db(tmp_path)
    assert _paths(db, sort=["path"]) == ["/photos/a.png", "/photos/M.png", "/photos/Z.png"]
    assert _paths(db, sort=["path"], direction=["desc"]) == ["/photos/Z.png", "/photos/M.png", "/photos/a.png"]


def test_browser_sorts_by_modified_size_and_confidence(tmp_path: Path):
    db = _db(tmp_path)
    assert _paths(db, sort=["modified"]) == ["/photos/M.png", "/photos/a.png", "/photos/Z.png"]
    assert _paths(db, sort=["size"]) == ["/photos/a.png", "/photos/M.png", "/photos/Z.png"]
    assert _paths(db, sort=["confidence"]) == ["/photos/M.png", "/photos/Z.png", "/photos/a.png"]


def test_browser_unknown_sort_falls_back_to_path(tmp_path: Path):
    assert _paths(_db(tmp_path), sort=["not-a-sort"]) == ["/photos/a.png", "/photos/M.png", "/photos/Z.png"]


def test_browser_legacy_table_sort_falls_back_safely(tmp_path: Path):
    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE analysis (path TEXT, vibe TEXT, confidence REAL)")
        conn.executemany("INSERT INTO analysis VALUES (?, ?, ?)", [("b.png", "Retro Blue", 0.5), ("a.png", "Retro Blue", 0.5)])
        conn.commit()
    rows, total = _query_rows(db, {"sort": ["size"]}, limit=10, offset=0)
    assert total == 2
    assert [row["path"] for row in rows] == ["a.png", "b.png"]
