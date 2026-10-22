from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
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


def _rollback_results(results: list[MoveResult]) -> None:
    """Restore freshly moved files if durable history cannot be committed."""
    failures: list[str] = []
    for result in reversed(results):
        if result.status != "moved":
            continue
        if not result.destination.is_file():
            failures.append(f"#{result.operation_id}: destination is missing")
            continue
        if result.source.exists() or result.source.is_symlink():
            failures.append(f"#{result.operation_id}: source path is occupied")
            continue
        try:
            result.source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(result.destination), str(result.source))
        except OSError as exc:
            failures.append(f"#{result.operation_id}: {exc}")
    if failures:
        raise OSError("history commit failed and rollback was incomplete: " + "; ".join(failures))


def record_batch(batch_id: str, results: tuple[MoveResult, ...], history_path: Path) -> int:
    """Atomically append successful moves to an auditable JSONL history file."""
    moved = [result for result in results if result.status == "moved"]
    if not moved:
        return 0

    history_path = history_path.expanduser()
    try:
        # Every operation after files have moved belongs inside this recovery
        # boundary, including hashing destinations and creating the history dir.
        history_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat()
        records = [
            {
                "event": "move",
                "batch_id": batch_id,
                "operation_id": result.operation_id,
                "source": str(result.source),
                "destination": str(result.destination),
                "sha256": _sha256(result.destination),
                "timestamp": timestamp,
            }
            for result in moved
        ]

        existing = history_path.read_bytes() if history_path.exists() else b""
        payload = existing + b"".join(
            (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8") for record in records
        )
        fd, temp_name = tempfile.mkstemp(prefix=f".{history_path.name}.", suffix=".tmp", dir=history_path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, history_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    except (OSError, TypeError, ValueError):
        _rollback_results(moved)
        raise

    return len(moved)


def load_batch(history_path: Path, batch_id: str) -> tuple[HistoryRecord, ...]:
    records: list[HistoryRecord] = []
    path = history_path.expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"history file not found: {path}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise OSError(f"could not read rollback history {path}: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt history at line {line_number}: {exc.msg}") from exc
        if not isinstance(item, dict):
            raise TypeError(f"invalid history record at line {line_number}: expected an object")
        if item.get("event") != "move" or item.get("batch_id") != batch_id:
            continue
        try:
            record = HistoryRecord(
                batch_id,
                int(item["operation_id"]),
                str(item["source"]),
                str(item["destination"]),
                str(item["sha256"]),
                str(item["timestamp"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid move record at line {line_number}: {exc}") from exc
        records.append(record)
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
        try:
            digest = _sha256(destination)
        except OSError as exc:
            results.append({"operation_id": record.operation_id, "status": "error", "source": str(source), "destination": str(destination), "detail": f"could not verify destination contents: {exc}"})
            continue
        if digest != record.sha256:
            results.append({"operation_id": record.operation_id, "status": "conflict", "source": str(source), "destination": str(destination), "detail": "destination contents changed since the move"})
            continue
        if source.exists() or source.is_symlink():
            results.append({"operation_id": record.operation_id, "status": "conflict", "source": str(source), "destination": str(destination), "detail": "original source path is occupied"})
            continue
        if dry_run:
            results.append({"operation_id": record.operation_id, "status": "planned", "source": str(source), "destination": str(destination), "detail": "safe to restore"})
            continue
        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(destination), str(source))
        except OSError as exc:
            results.append({"operation_id": record.operation_id, "status": "error", "source": str(source), "destination": str(destination), "detail": f"restore failed without overwriting the source: {exc}"})
            continue
        results.append({"operation_id": record.operation_id, "status": "restored", "source": str(source), "destination": str(destination), "detail": "hash verified before restore"})
    return tuple(results)


def list_history(history_path: Path) -> list[dict]:
    path = history_path.expanduser()
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
