from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Literal

from .vibes import VIBES, VibeScore

Verdict = Literal["correct", "incorrect", "partial"]
MAX_PREFERENCE_ADJUSTMENT = 0.05
PREFERENCE_STEP = 0.015


def _content_identity(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def apply_personal_preferences(
    scores: tuple[VibeScore, ...], adjustments: dict[str, float]
) -> tuple[VibeScore, ...]:
    """Apply bounded local-only ranking offsets without changing raw scores."""
    adjusted = (
        VibeScore(
            item.name,
            round(max(0.0, min(1.0, item.score + adjustments.get(item.name, 0.0))), 4),
        )
        for item in scores
    )
    return tuple(sorted(adjusted, key=lambda item: (-item.score, item.name)))


class PersonalCorrectionStore:
    """Private, content-deduplicated corrections stored in the local analysis DB."""

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS personal_corrections (
                content_hash TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                suggested_label TEXT NOT NULL,
                verdict TEXT NOT NULL CHECK(verdict IN ('correct','incorrect','partial')),
                corrected_label TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS personal_correction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL,
                previous_record TEXT,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_personal_corrections_label
                ON personal_corrections(suggested_label);
            """
        )
        self.connection.commit()

    def record(
        self,
        image: str | Path,
        suggested_label: str,
        verdict: Verdict,
        corrected_label: str | None = None,
    ) -> dict:
        path = Path(image).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"image does not exist: {path}")
        if suggested_label not in VIBES:
            raise ValueError(f"unknown suggested label: {suggested_label}")
        if verdict not in {"correct", "incorrect", "partial"}:
            raise ValueError("verdict must be correct, incorrect, or partial")
        if corrected_label is not None and corrected_label not in VIBES:
            raise ValueError(f"unknown corrected label: {corrected_label}")
        if verdict == "partial" and corrected_label == suggested_label:
            raise ValueError("a partially correct label must be corrected to a different vibe")
        digest = _content_identity(path)
        existing = self.connection.execute(
            "SELECT content_hash,path,suggested_label,verdict,corrected_label,updated_at "
            "FROM personal_corrections WHERE content_hash=?",
            (digest,),
        ).fetchone()
        previous = json.dumps(dict(existing), ensure_ascii=False) if existing else None
        self.connection.execute(
            "INSERT INTO personal_correction_history(content_hash,previous_record) VALUES(?,?)",
            (digest, previous),
        )
        self.connection.execute(
            """
            INSERT INTO personal_corrections(content_hash,path,suggested_label,verdict,corrected_label)
            VALUES(?,?,?,?,?)
            ON CONFLICT(content_hash) DO UPDATE SET
                path=excluded.path,
                suggested_label=excluded.suggested_label,
                verdict=excluded.verdict,
                corrected_label=excluded.corrected_label,
                updated_at=CURRENT_TIMESTAMP
            """,
            (digest, str(path), suggested_label, verdict, corrected_label),
        )
        self.connection.commit()
        return self.get_for_path(path) or {}

    def get_for_path(self, image: str | Path) -> dict | None:
        path = Path(image).expanduser().resolve()
        if not path.is_file():
            return None
        digest = _content_identity(path)
        row = self.connection.execute(
            "SELECT path,suggested_label,verdict,corrected_label,updated_at "
            "FROM personal_corrections WHERE content_hash=?",
            (digest,),
        ).fetchone()
        return dict(row) if row else None

    def adjustments(self) -> dict[str, float]:
        votes: dict[str, int] = {}
        rows = self.connection.execute(
            "SELECT suggested_label,verdict,corrected_label FROM personal_corrections"
        ).fetchall()
        for row in rows:
            suggested = str(row["suggested_label"])
            verdict = str(row["verdict"])
            if verdict == "correct":
                votes[suggested] = votes.get(suggested, 0) + 1
            elif verdict == "incorrect":
                votes[suggested] = votes.get(suggested, 0) - 1
            else:
                votes[suggested] = votes.get(suggested, 0) - 1
                corrected = row["corrected_label"]
                if corrected:
                    votes[str(corrected)] = votes.get(str(corrected), 0) + 1
        return {
            label: round(max(-MAX_PREFERENCE_ADJUSTMENT, min(MAX_PREFERENCE_ADJUSTMENT, count * PREFERENCE_STEP)), 4)
            for label, count in votes.items()
            if count
        }

    def list_corrections(self) -> list[dict]:
        rows = self.connection.execute(
            "SELECT path,suggested_label,verdict,corrected_label,updated_at "
            "FROM personal_corrections ORDER BY updated_at DESC,path COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]

    def undo_last(self) -> bool:
        row = self.connection.execute(
            "SELECT id,content_hash,previous_record FROM personal_correction_history ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return False
        self.connection.execute("DELETE FROM personal_correction_history WHERE id=?", (row["id"],))
        if row["previous_record"] is None:
            self.connection.execute(
                "DELETE FROM personal_corrections WHERE content_hash=?", (row["content_hash"],)
            )
        else:
            previous = json.loads(row["previous_record"])
            self.connection.execute(
                """
                INSERT OR REPLACE INTO personal_corrections
                (content_hash,path,suggested_label,verdict,corrected_label,updated_at)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    previous["content_hash"], previous["path"], previous["suggested_label"],
                    previous["verdict"], previous["corrected_label"], previous["updated_at"],
                ),
            )
        self.connection.commit()
        return True

    def clear(self) -> int:
        count = int(self.connection.execute("SELECT COUNT(*) FROM personal_corrections").fetchone()[0])
        self.connection.execute("DELETE FROM personal_corrections")
        self.connection.execute("DELETE FROM personal_correction_history")
        self.connection.commit()
        return count

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> PersonalCorrectionStore:
        return self

    def __exit__(self, *_args) -> None:
        self.close()
