from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from vibesorter.browser.server import _query_rows
from vibesorter.profile import AttributeValue, ImageProfile


def test_browser_profile_filter_matches_persisted_profile(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
        conn.execute("CREATE TABLE profiles (path TEXT PRIMARY KEY, taxonomy_version TEXT, profile TEXT)")
        profile = ImageProfile(colors=(AttributeValue("blue", 0.9),)).to_json()
        conn.execute("INSERT INTO images VALUES (?, ?, ?, ?, ?)", ("blue.png", 1, 1, "{}", json.dumps([])))
        conn.execute("INSERT INTO profiles VALUES (?, ?, ?)", ("blue.png", "1", profile))
        conn.commit()
    rows, total = _query_rows(db, {"colors": ["blue"]}, limit=10, offset=0)
    assert total == 1
    assert rows[0]["path"] == "blue.png"
    assert rows[0]["profile"]["colors"][0]["value"] == "blue"


def test_browser_list_payload_includes_profile_when_available(tmp_path: Path):
    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
        conn.execute("CREATE TABLE profiles (path TEXT PRIMARY KEY, taxonomy_version TEXT, profile TEXT)")
        profile = ImageProfile(brightness=AttributeValue("dark", 0.8)).to_json()
        conn.execute("INSERT INTO images VALUES (?, ?, ?, ?, ?)", ("dark.png", 1, 1, "{}", json.dumps([])))
        conn.execute("INSERT INTO profiles VALUES (?, ?, ?)", ("dark.png", "1", profile))
        conn.commit()
    rows, _ = _query_rows(db, {}, limit=10, offset=0)
    assert rows[0]["profile"]["brightness"]["value"] == "dark"
