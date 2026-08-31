from pathlib import Path
import sqlite3

from vibesorter.browser.server import _rows
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


def test_browser_filters_without_rescan(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE analysis (path TEXT, vibe TEXT)")
        conn.executemany("INSERT INTO analysis VALUES (?, ?)", [("a.png", "Retro Blue"), ("b.png", "Dark / Moody")])
        conn.commit()
    assert [r["path"] for r in _rows(db, "Retro Blue", None)] == ["a.png"]


def test_browser_renders_empty_state():
    page = render_page([])
    assert "No cached analysis matched" in page
    assert "no cloud upload" in page
