"""Local HTTP browser for VibeSorter analysis data.

The browser is intentionally a thin presentation layer: analysis remains owned by
VibeSorter's core and SQLite cache.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .ui import render_page


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(db_path: Path, vibe: str | None, query: str | None, limit: int = 100) -> list[dict]:
    if not db_path.exists():
        return []
    conn = _connect(db_path)
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        table = "analysis" if "analysis" in tables else ("images" if "images" in tables else None)
        if not table:
            return []
        columns = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        path_col = "path" if "path" in columns else ("image_path" if "image_path" in columns else None)
        vibe_col = "vibe" if "vibe" in columns else ("primary_vibe" if "primary_vibe" in columns else None)
        score_col = "confidence" if "confidence" in columns else ("confidence_score" if "confidence_score" in columns else None)
        if not path_col:
            return []
        where, args = [], []
        if vibe and vibe_col:
            where.append(f"{vibe_col} = ?")
            args.append(vibe)
        if query:
            where.append(f"{path_col} LIKE ?")
            args.append(f"%{query}%")
        sql = f"SELECT * FROM {table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " LIMIT ?"
        args.append(max(1, min(limit, 500)))
        result = []
        for row in conn.execute(sql, args):
            item = dict(row)
            item["path"] = item.get(path_col)
            item["vibe"] = item.get(vibe_col) if vibe_col else None
            item["confidence"] = item.get(score_col) if score_col else None
            result.append(item)
        return result
    finally:
        conn.close()


def create_app(db_path: str | Path = ".vibesorter/analysis.db"):
    db = Path(db_path)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content: str, content_type: str = "text/html; charset=utf-8") -> None:
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            vibe = params.get("vibe", [None])[0]
            query = params.get("q", [None])[0]
            if parsed.path == "/api/images":
                self._send(200, json.dumps(_rows(db, vibe, query), default=str), "application/json")
                return
            if parsed.path != "/":
                self._send(404, "Not found", "text/plain; charset=utf-8")
                return
            rows = _rows(db, vibe, query)
            self._send(200, render_page(rows, vibe=vibe, query=query))

        def log_message(self, *_args) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Browse VibeSorter analysis locally.")
    parser.add_argument("--db", default=".vibesorter/analysis.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), create_app(args.db))
    print(f"VibeSorter browser: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
