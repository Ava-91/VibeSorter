from __future__ import annotations

import argparse
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
        "confidence": "confidence" if "confidence" in columns else ("confidence_score" if "confidence_score" in columns else ""),
        "scores": "scores" if "scores" in columns else "",
        "features": "features" if "features" in columns else "",
    }


def _parse_scores(value: str | None) -> tuple[VibeScore, ...]:
    if not value:
        return ()
    try:
        return tuple(VibeScore(str(item["name"]), float(item["score"])) for item in json.loads(value))
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return ()


def _normalize_row(row: sqlite3.Row, columns: dict[str, str]) -> dict:
    item = dict(row)
    path = item.get(columns["path"]) if columns.get("path") else None
    vibe = item.get(columns["vibe"]) if columns.get("vibe") else None
    confidence = item.get(columns["confidence"]) if columns.get("confidence") else None
    scores = item.get(columns["scores"]) if columns.get("scores") else None
    parsed = _parse_scores(scores)
    if parsed and (vibe is None or confidence is None):
        vibe = vibe or parsed[0].name
        confidence = confidence if confidence is not None else confidence_score(parsed)
    item["path"] = str(path or "")
    item["vibe"] = vibe
    item["confidence"] = confidence
    return item


def _selected(params: dict[str, list[str]], name: str) -> tuple[str, ...]:
    values: list[str] = []
    for raw in params.get(name, []):
        values.extend(value.strip().casefold() for value in raw.split(",") if value.strip())
    return tuple(dict.fromkeys(values))


def _profile_matches(profile: ImageProfile | None, params: dict[str, list[str]]) -> bool:
    if profile is None:
        return not any(_selected(params, family) for family in ATTRIBUTE_FAMILIES)
    singles = {
        "media_type": profile.media_type.value if profile.media_type else None,
        "temperature": profile.temperature.value if profile.temperature else None,
        "saturation": profile.saturation.value if profile.saturation else None,
        "brightness": profile.brightness.value if profile.brightness else None,
    }
    for family, value in singles.items():
        wanted = _selected(params, family)
        if wanted and value not in wanted:
            return False
    multi = {
        "colors": {item.value for item in profile.colors},
        "vibes": {item.value for item in profile.vibes},
    }
    return all(not (wanted := _selected(params, family)) or multi[family].intersection(wanted) for family in multi)


def _profile_for(conn: sqlite3.Connection, path: str) -> ImageProfile | None:
    try:
        row = conn.execute("SELECT profile FROM profiles WHERE path=?", (path,)).fetchone()
        return ImageProfile.from_json(row[0]) if row else None
    except (TypeError, ValueError, KeyError, json.JSONDecodeError, sqlite3.OperationalError):
        return None


def _query_rows(
    db_path: Path,
    params_or_vibe: dict[str, list[str]] | str | None,
    query: str | None = None,
    *,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    if isinstance(params_or_vibe, dict):
        params = params_or_vibe
    else:
        params = {}
        if params_or_vibe:
            params["vibe"] = [params_or_vibe]
        if query:
            params["q"] = [query]
    if not db_path.exists():
        return [], 0
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        table, columns = _table_info(conn)
        if not table or not columns.get("path"):
            return [], 0
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY {columns['path']} COLLATE NOCASE").fetchall()
        query_text = (params.get("q", [""])[0] or "").casefold()
        vibe = (params.get("vibe", [""])[0] or "").casefold()
        matches: list[dict] = []
        for row in rows:
            item = _normalize_row(row, columns)
            if query_text and query_text not in item["path"].casefold():
                continue
            if vibe and str(item.get("vibe") or "").casefold() != vibe:
                parsed = _parse_scores(item.get(columns.get("scores", ""))) if columns.get("scores") else ()
                if not any(score.name.casefold() == vibe for score in parsed):
                    continue
            if not _profile_matches(_profile_for(conn, item["path"]), params):
                continue
            matches.append(item)
        total = len(matches)
        return matches[offset : offset + limit], total


def _rows(db_path: Path, vibe: str | None, query: str | None) -> list[dict]:
    rows, _ = _query_rows(db_path, vibe, query, limit=MAX_LIMIT, offset=0)
    return rows


def _vibe_summary(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        table, columns = _table_info(conn)
        if not table or not columns.get("path"):
            return []
        counts: dict[str, int] = defaultdict(int)
        totals: dict[str, float] = defaultdict(float)
        count_conf: dict[str, int] = defaultdict(int)
        if columns.get("vibe"):
            for vibe, confidence in conn.execute(f"SELECT {columns['vibe']}, {columns.get('confidence') or 'NULL'} FROM {table}"):
                label = str(vibe or "Unclassified")
                counts[label] += 1
                if isinstance(confidence, (int, float)):
                    totals[label] += float(confidence); count_conf[label] += 1
        elif columns.get("scores"):
            for (raw,) in conn.execute(f"SELECT {columns['scores']} FROM {table}"):
                scores = _parse_scores(raw)
                label = scores[0].name if scores else "Unclassified"
                counts[label] += 1
                if scores:
                    totals[label] += confidence_score(scores); count_conf[label] += 1
        return [{"vibe": label, "count": counts[label], "average_confidence": round(totals[label] / count_conf[label], 4) if count_conf[label] else None} for label in sorted(counts, key=lambda item: (-counts[item], item.casefold()))]


def _image_detail(db_path: Path, requested: str) -> dict | None:
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        table, columns = _table_info(conn)
        if not table or not columns.get("path"):
            return None
        row = conn.execute(f"SELECT * FROM {table} WHERE {columns['path']}=?", (requested,)).fetchone()
        if row is None:
            return None
        item = _normalize_row(row, columns)
        scores = _parse_scores(item.get(columns.get("scores", ""))) if columns.get("scores") else ()
        path = Path(item["path"]).expanduser()
        features = {}
        if columns.get("features"):
            try:
                raw = json.loads(item.get(columns["features"]) or "{}")
                features = {key: raw[key] for key in ("brightness", "saturation", "contrast", "warm_ratio", "cool_ratio", "grayscale_ratio", "dark_ratio", "light_ratio", "text_likelihood") if key in raw}
            except (TypeError, json.JSONDecodeError):
                pass
        profile = _profile_for(conn, item["path"])
        return {"path": item["path"], "vibe": item.get("vibe"), "confidence": float(item["confidence"]) if isinstance(item.get("confidence"), (int, float)) else (confidence_score(scores) if scores else 0.0), "ambiguous": not is_confident(scores) if scores else None, "scores": [{"name": s.name, "score": s.score} for s in scores], "profile": profile.to_dict() if profile else None, "features": features, "file": {"exists": path.is_file(), "size": path.stat().st_size if path.is_file() else None}}


def _image_path(db_path: Path, requested: str) -> Path | None:
    if not db_path.exists():
        return None
    with sqlite3.connect(db_path) as conn:
        table, columns = _table_info(conn)
        if not table or not columns.get("path"):
            return None
        row = conn.execute(f"SELECT {columns['path']} FROM {table} WHERE {columns['path']}=?", (requested,)).fetchone()
    if not row:
        return None
    path = Path(row[0]).expanduser()
    return path if path.is_file() else None


def create_app(db_path: str | Path = ".vibesorter/analysis.db", label_session=None):
    db = Path(db_path)

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content: str, content_type: str = "text/html; charset=utf-8") -> None:
            body = content.encode(); self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def _json(self, status: int, payload: dict) -> None:
            self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")
        def do_GET(self) -> None:
            parsed = urlparse(self.path); params = parse_qs(parsed.query)
            if parsed.path == "/label":
                if label_session is None: self._send(404, "Labeling session not configured", "text/plain; charset=utf-8")
                else: self._send(200, render_label_page(label_session))
                return
            if parsed.path == "/api/attributes":
                values = {"media_type": [item.value for item in MediaType], "colors": [item.value for item in Color], "temperature": [item.value for item in Temperature], "saturation": [item.value for item in Saturation], "brightness": [item.value for item in Brightness], "vibes": [item.value for item in Vibe]}
                self._json(200, {"families": ATTRIBUTE_FAMILIES, "values": values}); return
            if parsed.path == "/api/vibes":
                self._send(200, json.dumps({"items": _vibe_summary(db)}, ensure_ascii=False), "application/json; charset=utf-8"); return
            if parsed.path == "/api/image-details":
                detail = _image_detail(db, unquote(params.get("path", [""])[0]))
                if detail is None: self._send(404, "Image not found", "text/plain; charset=utf-8")
                else: self._json(200, detail)
                return
            try: limit = int(params.get("limit", [DEFAULT_LIMIT])[0]); page = max(1, int(params.get("page", [1])[0]))
            except ValueError: self._send(400, "Invalid pagination", "text/plain; charset=utf-8"); return
            if parsed.path == "/api/images":
                safe_limit = min(max(1, limit), MAX_LIMIT); rows, total = _query_rows(db, params, limit=safe_limit, offset=(page - 1) * safe_limit)
                self._json(200, {"items": rows, "page": page, "limit": safe_limit, "total": total}); return
            if parsed.path == "/api/image":
                image = _image_path(db, unquote(params.get("path", [""])[0]))
                if image is None: self._send(404, "Image not found", "text/plain; charset=utf-8")
                else:
                    try: self._send_bytes(200, image.read_bytes(), mimetypes.guess_type(image.name)[0] or "application/octet-stream")
                    except OSError: self._send(404, "Image not found", "text/plain; charset=utf-8")
                return
            if parsed.path != "/": self._send(404, "Not found", "text/plain; charset=utf-8"); return
            self._send(200, render_page())
        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if label_session is None or path not in {"/api/label/decision", "/api/label/undo"}:
                self._json(404, {"error": "Labeling session not configured" if label_session is None else "Not found"}); return
            if path == "/api/label/undo": self._json(200, {"undone": label_session.undo(), "labelled": label_session.labelled}); return
            try:
                length = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(length) or b"{}"); requested = str(data["path"]); label = data.get("label"); skip = bool(data.get("skip", False))
                candidate = next((item for item in label_session.remaining if str(item.path.resolve()) == str(Path(requested).expanduser().resolve())), None)
                if candidate is None: raise ValueError("unknown or already-labelled image")
                label_session.decide(candidate, None if skip else str(label))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc: self._json(400, {"error": str(exc)}); return
            self._json(200, {"ok": True, "labelled": label_session.labelled, "remaining": len(label_session.remaining)})
        def log_message(self, *_args) -> None: return
    return Handler


def run_server(db_path: str | Path = ".vibesorter/analysis.db", host: str = "127.0.0.1", port: int = 8765, label_session=None) -> None:
    server = ThreadingHTTPServer((host, port), create_app(db_path, label_session=label_session)); print(f"VibeSorter browser: http://{host}:{port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


def run_label_server(label_session, *, db_path: str | Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port, ), create_app(db_path, label_session=label_session)); print(f"VibeSorter labeling: http://{host}:{port}/label")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
