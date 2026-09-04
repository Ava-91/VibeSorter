from __future__ import annotations

import json
import mimetypes
import sqlite3
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from ..profile import ImageProfile
from ..taxonomy import (
    ATTRIBUTE_FAMILIES,
    Brightness,
    Color,
    MediaType,
    Saturation,
    Temperature,
    Vibe,
)
from ..vibes import VibeScore, confidence_score, is_confident
from .labeling_ui import render_label_page
from .ui import render_page

DEFAULT_LIMIT = 48
MAX_LIMIT = 120


def _table_info(conn: sqlite3.Connection) -> tuple[str | None, dict[str, str]]:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    table = "images" if "images" in tables else ("analysis" if "analysis" in tables else None)
    if table is None:
        return None, {}
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    return table, {
        "path": "path" if "path" in columns else ("image_path" if "image_path" in columns else ""),
        "vibe": "vibe" if "vibe" in columns else ("primary_vibe" if "primary_vibe" in columns else ""),
        "score": "score" if "score" in columns else ("primary_score" if "primary_score" in columns else ""),
        "scores": "scores" if "scores" in columns else "",
        "profile": "profile_json" if "profile_json" in columns else "",
    }


def _parse_scores(raw: object) -> tuple[VibeScore, ...]:
    if raw is None:
        return ()
    try:
        data = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return ()
    if not isinstance(data, list):
        return ()
    scores: list[VibeScore] = []
    for item in data:
        if isinstance(item, dict) and "name" in item and "score" in item:
            try:
                scores.append(VibeScore(str(item["name"]), float(item["score"])))
            except (TypeError, ValueError):
                continue
    return tuple(scores)


def _normalize_row(row: sqlite3.Row | tuple[object, ...], columns: list[str]) -> dict[str, object]:
    return dict(zip(columns, row, strict=False))


def _selected(params: dict[str, list[str]], family: str) -> set[str]:
    return {value.lower() for value in params.get(family, []) if value}


def _profile_matches(profile: ImageProfile | None, params: dict[str, list[str]]) -> bool:
    if profile is None:
        return not any(_selected(params, family) for family in ATTRIBUTE_FAMILIES)
    values = {
        "media_type": {profile.media_type.value.lower()} if profile.media_type else set(),
        "colors": {item.value.lower() for item in profile.colors},
        "temperature": {profile.temperature.value.lower()} if profile.temperature else set(),
        "saturation": {profile.saturation.value.lower()} if profile.saturation else set(),
        "brightness": {profile.brightness.value.lower()} if profile.brightness else set(),
        "vibes": {item.value.lower() for item in profile.vibes},
    }
    return all(not _selected(params, family) or _selected(params, family) <= values[family] for family in ATTRIBUTE_FAMILIES)


def _profile_for(row: dict[str, object], columns: dict[str, str]) -> ImageProfile | None:
    field = columns.get("profile")
    if not field or not row.get(field):
        return None
    try:
        return ImageProfile.from_json(str(row[field]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _query_rows(
    db_path: Path,
    params_or_vibe: dict[str, list[str]] | str | None = None,
    query: str | None = None,
    *,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, object]], int]:
    if isinstance(params_or_vibe, dict):
        params = params_or_vibe
    else:
        params = {}
        if params_or_vibe:
            params["vibe"] = [params_or_vibe]
        if query:
            params["q"] = [query]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        table, columns = _table_info(conn)
        if table is None or not columns["path"]:
            return [], 0
        select_columns = [columns["path"]]
        for key in ("vibe", "score", "scores", "profile"):
            if columns[key] and columns[key] not in select_columns:
                select_columns.append(columns[key])
        where: list[str] = []
        values: list[str] = []
        search = params.get("q", [""])[0].strip()
        if search:
            where.append(f"LOWER({columns['path']}) LIKE ?")
            values.append(f"%{search.lower()}%")
        sql = f"SELECT {', '.join(select_columns)} FROM {table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f" ORDER BY {columns['path']} LIMIT ? OFFSET ?"
        raw_rows = conn.execute(sql, (*values, limit, offset)).fetchall()
        count_sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            count_sql += " WHERE " + " AND ".join(where)
        total = int(conn.execute(count_sql, values).fetchone()[0])
        rows = [_normalize_row(row, select_columns) for row in raw_rows]
        filtered: list[dict[str, object]] = []
        for row in rows:
            profile = _profile_for(row, columns)
            if _profile_matches(profile, params):
                filtered.append(row)
        return filtered, total
    finally:
        conn.close()


def _rows(db_path: Path, vibe: str | None, query: str | None) -> list[dict[str, object]]:
    rows, _ = _query_rows(db_path, vibe, query, limit=MAX_LIMIT, offset=0)
    return rows


def _vibe_summary(scores: tuple[VibeScore, ...]) -> str:
    if not scores:
        return "Unclassified"
    selected = [score.name for score in scores if score.score >= 0.45]
    return ", ".join(selected) if selected else scores[0].name


def _image_detail(db_path: Path, path: str) -> dict[str, object] | None:
    rows, _ = _query_rows(db_path, {}, path, limit=1, offset=0)
    return rows[0] if rows else None


def _image_path(db_path: Path, raw_path: str) -> Path | None:
    detail = _image_detail(db_path, raw_path)
    if detail is None:
        return None
    path_value = detail.get("path") or detail.get("image_path")
    return Path(str(path_value)) if path_value else None


def create_app(db_path: Path, *, image_root: Path | None = None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if parsed.path == "/":
                rows, _ = _query_rows(db_path, params, limit=DEFAULT_LIMIT, offset=0)
                body = render_page(rows)
                self._send(200, body, "text/html; charset=utf-8")
                return
            if parsed.path == "/api/images":
                try:
                    limit = min(MAX_LIMIT, max(1, int(params.get("limit", [DEFAULT_LIMIT])[0])))
                    offset = max(0, int(params.get("offset", [0])[0]))
                except ValueError:
                    self._send(400, "invalid pagination", "text/plain; charset=utf-8")
                    return
                rows, total = _query_rows(db_path, params, limit=limit, offset=offset)
                self._send_json(200, {"items": rows, "total": total})
                return
            if parsed.path == "/api/attributes":
                self._send_json(200, {
                    "media_type": [item.value for item in MediaType],
                    "colors": [item.value for item in Color],
                    "temperature": [item.value for item in Temperature],
                    "saturation": [item.value for item in Saturation],
                    "brightness": [item.value for item in Brightness],
                    "vibes": [item.value for item in Vibe],
                })
                return
            if parsed.path == "/api/vibes":
                self._send_json(200, {"vibes": [item.value for item in Vibe]})
                return
            if parsed.path == "/api/image-details":
                path = unquote(params.get("path", [""])[0])
                detail = _image_detail(db_path, path)
                if detail is None:
                    self._send_json(404, {"error": "image not found"})
                else:
                    self._send_json(200, detail)
                return
            if parsed.path == "/api/image":
                raw_path = unquote(params.get("path", [""])[0])
                path = _image_path(db_path, raw_path)
                if path is None or not path.is_file():
                    self._send(404, "image not found", "text/plain; charset=utf-8")
                    return
                if image_root is not None:
                    try:
                        path.resolve().relative_to(image_root.resolve())
                    except ValueError:
                        self._send(403, "image outside configured root", "text/plain; charset=utf-8")
                        return
                data = path.read_bytes()
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                self._send(200, data, content_type)
                return
            if parsed.path == "/label":
                self._send(200, render_label_page(), "text/html; charset=utf-8")
                return
            self._send(404, "not found", "text/plain; charset=utf-8")

        def _send(self, status: int, body: str | bytes, content_type: str) -> None:
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, status: int, payload: object) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def run_server(db_path: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), create_app(db_path))
    try:
        server.serve_forever()
    finally:
        server.server_close()


def run_label_server(host: str = "127.0.0.1", port: int = 8766) -> None:
    server = ThreadingHTTPServer((host, port), create_app(Path(".vibesorter/analysis.db")))
    try:
        server.serve_forever()
    finally:
        server.server_close()
