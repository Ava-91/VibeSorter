from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from ..vibes import VibeScore, confidence_score
from .ui import render_page

DEFAULT_LIMIT = 48
MAX_LIMIT = 120


def _table_info(conn: sqlite3.Connection) -> tuple[str | None, dict[str, str]]:
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    table = "images" if "images" in tables else ("analysis" if "analysis" in tables else None)
    if table is None:
        return None, {}
    columns = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    return table, {
        "path": "path" if "path" in columns else ("image_path" if "image_path" in columns else ""),
        "vibe": "vibe" if "vibe" in columns else ("primary_vibe" if "primary_vibe" in columns else ""),
        "confidence": "confidence" if "confidence" in columns else ("confidence_score" if "confidence_score" in columns else ""),
        "scores": "scores" if "scores" in columns else "",
    }


def _normalize_row(row: sqlite3.Row, columns: dict[str, str]) -> dict:
    item = dict(row)
    path = item.get(columns["path"]) if columns["path"] else None
    vibe = item.get(columns["vibe"]) if columns["vibe"] else None
    confidence = item.get(columns["confidence"]) if columns["confidence"] else None
    scores = item.get(columns["scores"]) if columns["scores"] else None
    if scores and (vibe is None or confidence is None):
        try:
            parsed = json.loads(scores)
            parsed_scores = tuple(VibeScore(str(score["name"]), float(score["score"])) for score in parsed)
            if parsed_scores:
                vibe = vibe or parsed_scores[0].name
                confidence = confidence if confidence is not None else confidence_score(parsed_scores)
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            pass
    item["path"] = str(path or "")
    item["vibe"] = vibe
    item["confidence"] = confidence
    return item


def _query_rows(
    db_path: Path,
    vibe: str | None,
    query: str | None,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[dict], int]:
    if not db_path.exists():
        return [], 0
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        table, columns = _table_info(conn)
        path_col = columns.get("path")
        if not table or not path_col:
            return [], 0
        where: list[str] = []
        args: list[str] = []
        vibe_col = columns.get("vibe")
        if vibe and vibe_col:
            where.append(f"{vibe_col} = ?")
            args.append(vibe)
        elif vibe and columns.get("scores"):
            where.append(f"{columns['scores']} LIKE ?")
            args.append(f"%\"name\": {json.dumps(vibe, ensure_ascii=False)}%")
        if query:
            where.append(f"LOWER({path_col}) LIKE LOWER(?)")
            args.append(f"%{query}%")
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        total = conn.execute(f"SELECT COUNT(*) FROM {table}{clause}", args).fetchone()[0]
        sql = f"SELECT * FROM {table}{clause} ORDER BY {path_col} COLLATE NOCASE LIMIT ? OFFSET ?"
        rows = [_normalize_row(row, columns) for row in conn.execute(sql, [*args, limit, offset])]
        return rows, total


def _vibe_summary(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        table, columns = _table_info(conn)
        if not table or not columns.get("path"):
            return []
        counts: dict[str, int] = defaultdict(int)
        confidence_totals: dict[str, float] = defaultdict(float)
        confidence_counts: dict[str, int] = defaultdict(int)
        if columns.get("vibe"):
            select = columns["vibe"]
            confidence_col = columns.get("confidence")
            rows = conn.execute(f"SELECT {select}, {confidence_col or 'NULL'} FROM {table}")
            for vibe, confidence in rows:
                label = str(vibe or "Unclassified")
                counts[label] += 1
                if isinstance(confidence, (int, float)):
                    confidence_totals[label] += float(confidence)
                    confidence_counts[label] += 1
        elif columns.get("scores"):
            for (scores,) in conn.execute(f"SELECT {columns['scores']} FROM {table}"):
                try:
                    parsed = json.loads(scores)
                    if not parsed:
                        counts["Unclassified"] += 1
                        continue
                    label = str(parsed[0]["name"])
                    parsed_scores = tuple(VibeScore(str(item["name"]), float(item["score"])) for item in parsed)
                    counts[label] += 1
                    confidence_totals[label] += confidence_score(parsed_scores)
                    confidence_counts[label] += 1
                except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                    counts["Unclassified"] += 1
        return [
            {
                "vibe": label,
                "count": counts[label],
                "average_confidence": round(confidence_totals[label] / confidence_counts[label], 4) if confidence_counts[label] else None,
            }
            for label in sorted(counts, key=lambda item: (-counts[item], item.casefold()))
        ]


def _rows(db_path: Path, vibe: str | None, query: str | None, limit: int = DEFAULT_LIMIT) -> list[dict]:
    rows, _ = _query_rows(db_path, vibe, query, limit=limit)
    return rows


def _image_path(db_path: Path, requested: str) -> Path | None:
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        table, columns = _table_info(conn)
        path_col = columns.get("path")
        if not table or not path_col:
            return None
        row = conn.execute(f"SELECT {path_col} FROM {table} WHERE {path_col} = ?", (requested,)).fetchone()
    if not row:
        return None
    path = Path(row[0]).expanduser()
    return path if path.is_file() else None


def create_app(db_path: str | Path = ".vibesorter/analysis.db"):
    db = Path(db_path)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content: str, content_type: str = "text/html; charset=utf-8") -> None:
            body = content.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
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
            if parsed.path == "/api/vibes":
                self._send(200, json.dumps({"items": _vibe_summary(db)}, ensure_ascii=False), "application/json; charset=utf-8")
                return
            try:
                limit = int(params.get("limit", [DEFAULT_LIMIT])[0])
                page = max(1, int(params.get("page", [1])[0]))
            except ValueError:
                self._send(400, "Invalid pagination", "text/plain; charset=utf-8")
                return
            if parsed.path == "/api/images":
                safe_limit = min(max(1, limit), MAX_LIMIT)
                rows, total = _query_rows(db, vibe, query, limit=safe_limit, offset=(page - 1) * safe_limit)
                payload = {"items": rows, "page": page, "limit": safe_limit, "total": total}
                self._send(200, json.dumps(payload, default=str), "application/json; charset=utf-8")
                return
            if parsed.path == "/api/image":
                requested = unquote(params.get("path", [""])[0])
                image = _image_path(db, requested)
                if image is None:
                    self._send(404, "Image not found", "text/plain; charset=utf-8")
                    return
                try:
                    self._send_bytes(200, image.read_bytes(), mimetypes.guess_type(image.name)[0] or "application/octet-stream")
                except OSError:
                    self._send(404, "Image not found", "text/plain; charset=utf-8")
                return
            if parsed.path != "/":
                self._send(404, "Not found", "text/plain; charset=utf-8")
                return
            self._send(200, render_page())

        def log_message(self, *_args) -> None:
            return

    return Handler


def run_server(db_path: str | Path = ".vibesorter/analysis.db", host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), create_app(db_path))
    print(f"VibeSorter browser: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Browse VibeSorter analysis locally.")
    parser.add_argument("--db", default=".vibesorter/analysis.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(args.db, args.host, args.port)


if __name__ == "__main__":
    main()
