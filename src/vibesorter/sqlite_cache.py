from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .features import ColorSample, ImageFeatures, SpatialRegion
from .vibes import VibeScore

SCHEMA_VERSION = 1
DEFAULT_SQLITE_PATH = Path('.vibesorter') / 'analysis.db'


def _identity(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def _feature_to_dict(features: ImageFeatures) -> dict:
    data = asdict(features)
    data['path'] = str(features.path)
    return data


def _feature_from_dict(data: dict) -> ImageFeatures:
    return ImageFeatures(
        path=Path(data['path']), average_rgb=tuple(data['average_rgb']), average_hsv=tuple(data['average_hsv']),
        brightness=float(data['brightness']), saturation=float(data['saturation']), contrast=float(data['contrast']),
        warm_ratio=float(data['warm_ratio']), cool_ratio=float(data['cool_ratio']), grayscale_ratio=float(data['grayscale_ratio']),
        dark_ratio=float(data['dark_ratio']), light_ratio=float(data['light_ratio']), text_likelihood=float(data['text_likelihood']),
        colors=tuple(ColorSample(tuple(item['rgb']), float(item['proportion'])) for item in data.get('colors', [])),
        regions=tuple(SpatialRegion(float(item['brightness']), float(item['saturation']), float(item.get('warm_ratio', 0.0)), float(item.get('cool_ratio', 0.0))) for item in data.get('regions', [])),
        center_brightness_delta=float(data.get('center_brightness_delta', 0.0)), center_saturation_delta=float(data.get('center_saturation_delta', 0.0)),
    )


class SQLiteAnalysisCache:
    """Transactional local cache backed by SQLite, with one row per analyzed image."""

    def __init__(self, path: str | Path = DEFAULT_SQLITE_PATH) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute('PRAGMA foreign_keys = ON')
        self.connection.execute('PRAGMA journal_mode = WAL')
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS images (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                features TEXT NOT NULL,
                scores TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_images_mtime ON images(mtime_ns);
        ''')
        self.connection.execute("INSERT OR IGNORE INTO metadata(key, value) VALUES('schema_version', ?)", (str(SCHEMA_VERSION),))
        self.connection.commit()

    def get(self, path: str | Path):
        image_path = Path(path).expanduser()
        try: size, mtime_ns = _identity(image_path)
        except OSError: return None
        row = self.connection.execute('SELECT size, mtime_ns, features, scores FROM images WHERE path = ?', (str(image_path),)).fetchone()
        if row is None or (row[0], row[1]) != (size, mtime_ns): return None
        try:
            features = _feature_from_dict(json.loads(row[2]))
            scores = tuple(VibeScore(item['name'], float(item['score'])) for item in json.loads(row[3]))
            return features, scores
        except (TypeError, ValueError, KeyError, json.JSONDecodeError): return None

    def entries(self):
        rows = self.connection.execute('SELECT path FROM images ORDER BY path COLLATE NOCASE').fetchall()
        results = []
        for (path,) in rows:
            result = self.get(path)
            if result is not None: results.append((Path(path), result[0], result[1]))
        return tuple(results)

    def set(self, path: str | Path, features: ImageFeatures, scores: tuple[VibeScore, ...]) -> None:
        image_path = Path(path).expanduser()
        try: size, mtime_ns = _identity(image_path)
        except OSError: size, mtime_ns = -1, -1
        self.connection.execute('''INSERT INTO images(path, size, mtime_ns, features, scores) VALUES(?,?,?,?,?)
            ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime_ns=excluded.mtime_ns, features=excluded.features, scores=excluded.scores''',
            (str(image_path), size, mtime_ns, json.dumps(_feature_to_dict(features), ensure_ascii=False), json.dumps([asdict(s) for s in scores])))

    def remove_missing(self) -> int:
        paths = [row[0] for row in self.connection.execute('SELECT path FROM images').fetchall()]
        removed = 0
        for path in paths:
            if not Path(path).exists():
                self.connection.execute('DELETE FROM images WHERE path = ?', (path,)); removed += 1
        return removed

    def save(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
