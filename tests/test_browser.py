from pathlib import Path
import json
import sqlite3

from vibesorter.browser.server import _image_path, _query_rows, _rows, _vibe_summary
from vibesorter.browser.ui import render_page


def test_browser_reads_cached_analysis(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE analysis (path TEXT, vibe TEXT, confidence REAL)")
        conn.execute("INSERT INTO analysis VALUES (?, ?, ?)", ("/photos/night.png", "Dark / Moody", 0.82))
        conn.commit()
    rows = _rows(db, "Dark / Moody", None)
    assert rows[0]["path"] == "/photos/night.png"
    assert rows[0]["confidence"] == 0.82


def test_browser_reads_current_sqlite_score_rows(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
        conn.execute(
            "INSERT INTO images VALUES (?, ?, ?, ?, ?)",
            ("/photos/night.png", 10, 20, "{}", json.dumps([
                {"name": "Dark / Moody", "score": 0.82},
                {"name": "Retro Blue", "score": 0.60},
            ])),
        )
        conn.commit()
    rows = _rows(db, None, None)
    assert rows[0]["vibe"] == "Dark / Moody"
    assert rows[0]["confidence"] == 0.841


def test_browser_filters_without_rescan(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE analysis (path TEXT, vibe TEXT)")
        conn.executemany("INSERT INTO analysis VALUES (?, ?)", [("a.png", "Retro Blue"), ("b.png", "Dark / Moody")])
        conn.commit()
    assert [r["path"] for r in _rows(db, "Retro Blue", None)] == ["a.png"]


def test_browser_paginates_cached_rows(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE analysis (path TEXT, vibe TEXT)")
        conn.executemany("INSERT INTO analysis VALUES (?, ?)", [(f"{i:02}.png", "Retro Blue") for i in range(5)])
        conn.commit()
    first, total = _query_rows(db, "Retro Blue", None, limit=2, offset=0)
    second, _ = _query_rows(db, "Retro Blue", None, limit=2, offset=2)
    assert total == 5
    assert [row["path"] for row in first] == ["00.png", "01.png"]
    assert [row["path"] for row in second] == ["02.png", "03.png"]


def test_browser_vibe_summary_uses_current_sqlite_scores(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
        rows = [
            ("a.png", 1, 1, "{}", json.dumps([{"name": "Dark / Moody", "score": 0.8}, {"name": "Retro Blue", "score": 0.5}])),
            ("b.png", 1, 1, "{}", json.dumps([{ "name": "Dark / Moody", "score": 0.7}, {"name": "Retro Blue", "score": 0.4}])),
            ("c.png", 1, 1, "{}", json.dumps([{ "name": "Soft / Pastel", "score": 0.7}, {"name": "Bright / Colorful", "score": 0.4}])),
        ]
        conn.executemany("INSERT INTO images VALUES (?, ?, ?, ?, ?)", rows)
        conn.commit()
    summary = _vibe_summary(db)
    assert summary[0]["vibe"] == "Dark / Moody"
    assert summary[0]["count"] == 2
    assert summary[1]["vibe"] == "Soft / Pastel"
    assert summary[1]["count"] == 1


def test_browser_image_path_only_serves_cached_existing_files(tmp_path: Path):
    db = tmp_path / "analysis.db"
    image = tmp_path / "photo.png"
    image.write_bytes(b"not-a-real-png")
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE analysis (path TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO analysis VALUES (?)", (str(image),))
        conn.commit()
    assert _image_path(db, str(image)) == image
    assert _image_path(db, str(tmp_path / "secret.txt")) is None


def test_browser_renders_empty_state():
    page = render_page([])
    assert "No cached analysis matched" in page
    assert "no cloud upload" in page


def test_browser_renders_lazy_image_grid():
    page = render_page()
    assert "loading='lazy'" in page
    assert "api/images" in page
    assert "load-more" in page
    assert "api/vibes" in page
