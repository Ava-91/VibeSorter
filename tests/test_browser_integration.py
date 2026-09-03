from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from urllib.request import urlopen

from PIL import Image

from vibesorter.browser.server import create_app
from http.server import ThreadingHTTPServer


def test_browser_end_to_end_with_real_local_images(tmp_path: Path):
    library = tmp_path / "library"
    library.mkdir()
    images = []
    for index, color in enumerate(((20, 30, 50), (180, 80, 40), (220, 220, 220))):
        path = library / f"image-{index}.png"
        Image.new("RGB", (32, 32), color).save(path)
        images.append(path)

    db = tmp_path / "analysis.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE images (path TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, features TEXT, scores TEXT)")
        for index, path in enumerate(images):
            scores = [
                {"name": "Dark / Moody" if index == 0 else "Red / Warm" if index == 1 else "Black & White", "score": 0.82},
                {"name": "Retro Blue", "score": 0.60},
            ]
            conn.execute(
                "INSERT INTO images VALUES (?, ?, ?, ?, ?)",
                (str(path), path.stat().st_size, path.stat().st_mtime_ns, json.dumps({"brightness": index / 10}), json.dumps(scores)),
            )
        conn.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_app(db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urlopen(f"{base}/api/images?limit=2&page=1", timeout=3) as response:
            payload = json.load(response)
        assert payload["total"] == 3
        assert len(payload["items"]) == 2
        assert payload["items"][0]["path"] == str(images[0])

        with urlopen(f"{base}/api/image?path={images[0]}", timeout=3) as response:
            body = response.read()
            content_type = response.headers["Content-Type"]
        assert body == images[0].read_bytes()
        assert content_type.startswith("image/png")

        with urlopen(f"{base}/api/image-details?path={images[1]}", timeout=3) as response:
            detail = json.load(response)
        assert detail["path"] == str(images[1])
        assert detail["vibe"] == "Red / Warm"
        assert detail["scores"][1]["name"] == "Retro Blue"
        assert detail["file"]["exists"] is True

        with urlopen(f"{base}/", timeout=3) as response:
            page = response.read().decode("utf-8")
        assert "VibeSorter" in page
        assert "loading='lazy'" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()
