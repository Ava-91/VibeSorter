from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .operations import MoveResult


@dataclass(frozen=True, slots=True)
class HistoryRecord:
    batch_id: str
    operation_id: int
    source: str
    destination: str
    sha256: str
    timestamp: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_batch(batch_id: str, results: tuple[MoveResult, ...], history_path: Path) -> int:
    """Append successful moves to an auditable JSONL history file."""
    moved = [result for result in results if result.status == "moved"]
    if not moved:
        return 0
    history_path = history_path.expanduser()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with history_path.open("a", encoding="utf-8") as handle:
        for result in moved:
            handle.write(json.dumps({
                "event": "move",
                "batch_id": batch_id,
                "operation_id": result.operation_id,
                "source": str(result.source),
                "destination": str(result.destination),
                "sha256": _sha256(result.destination),
                "timestamp": timestamp,
            }, ensure_ascii=False) + "\n")
    return len(moved)


def load_batch(history_path: Path, batch_id: str) -> tuple[HistoryRecord, ...]:
    records: list[HistoryRecord] = []
    path = history_path.expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"history file not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("event") == "move" and item.get("batch_id") == batch_id:
            records.append(HistoryRecord(batch_id, int(item["operation_id"]), item["source"], item["destination"], item["sha256"], item["timestamp"]))
    if not records:
        raise ValueError(f"batch not found: {batch_id}")
    return tuple(sorted(records, key=lambda record: record.operation_id, reverse=True))


def rollback_batch(history_path: Path, batch_id: str, *, confirm: bool = False, dry_run: bool = False) -> tuple[dict, ...]:
    """Safely reverse a completed batch without overwriting unrelated files."""
    if not confirm and not dry_run:
        raise ValueError("rollback requires explicit confirmation")
    records = load_batch(history_path, batch_id)
    results: list[dict] = []
    for record in records:
        destination = Path(record.destination).expanduser()
        source = Path(record.source).expanduser()
        if not destination.is_file():
            results.append({"operation_id": record.operation_id, "status": "missing", "source": str(source), "destination": str(destination), "detail": "moved file is no longer at its recorded destination"})
            continue
        if _sha256(destination) != record.sha256:
            results.append({"operation_id": record.operation_id, "status": "conflict", "source": str(source), "destination": str(destination), "detail": "destination contents changed since the move"})
            continue
        if source.exists():
            results.append({"operation_id": record.operation_id, "status": "conflict", "source": str(source), "destination": str(destination), "detail": "original source path is occupied"})
            continue
        if dry_run:
            results.append({"operation_id": record.operation_id, "status": "planned", "source": str(source), "destination": str(destination), "detail": "safe to restore"})
            continue
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destination), str(source))
        results.append({"operation_id": record.operation_id, "status": "restored", "source": str(source), "destination": str(destination), "detail": "hash verified before restore"})
    return tuple(results)


def list_history(history_path: Path) -> list[dict]:
    path = history_path.expanduser()
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
