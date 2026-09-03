from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .indexer import index_folder
from .vibes import VIBES, confidence_score, is_confident, VibeScore


@dataclass(frozen=True, slots=True)
class LabelCandidate:
    path: Path
    prediction: str
    confidence: float
    ambiguous: bool
    scores: tuple[VibeScore, ...]

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "prediction": self.prediction,
            "confidence": self.confidence,
            "ambiguous": self.ambiguous,
            "scores": [{"name": score.name, "score": score.score} for score in self.scores],
        }


def _parse_scores(value: str) -> tuple[VibeScore, ...]:
    try:
        return tuple(VibeScore(str(item["name"]), float(item["score"])) for item in json.loads(value))
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return ()


def load_completed_labels(output: str | Path) -> dict[str, str]:
    path = Path(output).expanduser()
    if not path.exists():
        return {}
    completed: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            image_path = str(Path(data["path"]).expanduser().resolve())
            label = str(data["label"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid labeling record on line {line_number}") from exc
        if label not in VIBES:
            raise ValueError(f"unknown vibe label on line {line_number}: {label}")
        completed[image_path] = label
    return completed


def _write_completed(output: Path, records: dict[str, dict]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for path in sorted(records, key=str.casefold):
            handle.write(json.dumps(records[path], ensure_ascii=False) + "\n")
    temporary.replace(output)


def save_label(
    output: str | Path,
    candidate: LabelCandidate,
    label: str,
) -> None:
    if label not in VIBES:
        raise ValueError(f"unknown vibe label: {label}")
    destination = Path(output).expanduser()
    existing = load_completed_labels(destination)
    records = {
        path: {"path": path, "label": value, "source": "human", "prediction": None, "confidence": None}
        for path, value in existing.items()
    }
    key = str(candidate.path.resolve())
    records[key] = {
        "path": key,
        "label": label,
        "source": "human",
        "prediction": candidate.prediction,
        "confidence": candidate.confidence,
    }
    _write_completed(destination, records)


def build_candidates(
    db: str | Path,
    folder: str | Path,
    *,
    count: int,
    uncertain_first: bool = True,
) -> tuple[LabelCandidate, ...]:
    if count < 1:
        raise ValueError("count must be at least 1")
    root = Path(folder).expanduser().resolve()
    database = Path(db).expanduser()
    if not database.exists():
        raise FileNotFoundError(f"analysis database not found: {database}; run index first")

    candidates: list[LabelCandidate] = []
    prefix = str(root)
    with sqlite3.connect(database) as conn:
        rows = conn.execute("SELECT path, scores FROM images ORDER BY path COLLATE NOCASE").fetchall()
    for raw_path, raw_scores in rows:
        path = Path(raw_path).expanduser()
        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue
        scores = _parse_scores(raw_scores)
        if not scores:
            continue
        candidates.append(
            LabelCandidate(
                path=path.resolve(),
                prediction=scores[0].name,
                confidence=confidence_score(scores),
                ambiguous=not is_confident(scores),
                scores=scores,
            )
        )

    if uncertain_first:
        candidates.sort(key=lambda item: (not item.ambiguous, item.confidence, str(item.path).casefold()))
    else:
        candidates.sort(key=lambda item: str(item.path).casefold())
    return tuple(candidates[:count])


def prepare_labeling(
    folder: str | Path,
    *,
    db: str | Path,
    count: int,
    workers: int = 8,
    uncertain_first: bool = True,
) -> tuple[LabelCandidate, ...]:
    index_folder(folder, workers=workers)
    return build_candidates(db, folder, count=count, uncertain_first=uncertain_first)


class LabelSession:
    """In-memory review state with incremental local JSONL persistence."""

    def __init__(self, candidates: tuple[LabelCandidate, ...], output: str | Path) -> None:
        self.candidates = candidates
        self.output = Path(output).expanduser()
        self.completed = load_completed_labels(self.output)
        self.history: list[tuple[str, str | None]] = []

    @property
    def remaining(self) -> tuple[LabelCandidate, ...]:
        return tuple(item for item in self.candidates if str(item.path.resolve()) not in self.completed)

    @property
    def labelled(self) -> int:
        return len(self.completed)

    def decide(self, candidate: LabelCandidate, label: str | None) -> None:
        key = str(candidate.path.resolve())
        if candidate not in self.candidates:
            raise ValueError("candidate is not part of this session")
        if label is not None and label not in VIBES:
            raise ValueError(f"unknown vibe label: {label}")
        previous = self.completed.get(key)
        self.history.append((key, previous))
        if label is None:
            return
        save_label(self.output, candidate, label)
        self.completed[key] = label

    def undo(self) -> bool:
        if not self.history:
            return False
        key, previous = self.history.pop()
        if previous is None:
            self.completed.pop(key, None)
            records = {path: {"path": path, "label": label, "source": "human"} for path, label in self.completed.items()}
            if records:
                _write_completed(self.output, records)
            elif self.output.exists():
                self.output.unlink()
            return True
        candidate = next((item for item in self.candidates if str(item.path.resolve()) == key), None)
        if candidate is None:
            return False
        save_label(self.output, candidate, previous)
        self.completed[key] = previous
        return True
