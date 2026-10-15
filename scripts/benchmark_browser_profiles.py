from __future__ import annotations

import argparse
import sqlite3
import tempfile
import time
from pathlib import Path

from vibesorter.browser.server import _query_rows
from vibesorter.profile import AttributeValue, ImageProfile


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark SQLite-backed browser profile filtering and pagination.")
    parser.add_argument("--rows", type=int, default=50000, help="Synthetic cached images to generate (default: 50000).")
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be positive")

    blue = ImageProfile(colors=(AttributeValue("blue", 0.9),)).to_json()
    red = ImageProfile(colors=(AttributeValue("red", 0.9),)).to_json()
    with tempfile.TemporaryDirectory(prefix="vibesorter-browser-bench-") as directory:
        db = Path(directory) / "analysis.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
            conn.execute("CREATE TABLE profiles (path TEXT PRIMARY KEY, taxonomy_version TEXT, profile TEXT)")
            images = []
            profiles = []
            for index in range(args.rows):
                path = f"image-{index:08}.png"
                images.append((path, 1, 1, "{}", "[]"))
                profiles.append((path, "2.0", blue if index % 2 == 0 else red))
            conn.executemany("INSERT INTO images VALUES (?, ?, ?, ?, ?)", images)
            conn.executemany("INSERT INTO profiles VALUES (?, ?, ?)", profiles)
            conn.commit()

        started = time.perf_counter()
        rows, total = _query_rows(db, {"colors": ["blue"]}, limit=48, offset=min(1000, args.rows // 4))
        elapsed = time.perf_counter() - started
        print(f"images={args.rows} filtered_total={total} returned={len(rows)} page_size=48 elapsed_ms={elapsed * 1000:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
