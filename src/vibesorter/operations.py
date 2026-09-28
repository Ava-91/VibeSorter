from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .path_safety import canonical_path, same_path
from .review import ReviewedOperation


@dataclass(frozen=True, slots=True)
class MoveResult:
    operation_id: int
    status: str
    source: Path
    destination: Path
    detail: str = ""


def apply_reviewed(reviewed: tuple[ReviewedOperation, ...], *, confirm: bool = False, dry_run: bool = False) -> tuple[MoveResult, ...]:
    """Apply only accepted operations after explicit confirmation."""
    if not confirm and not dry_run:
        raise ValueError("filesystem changes require explicit confirmation")
    results: list[MoveResult] = []
    planned_destinations: set[Path] = set()
    for item in (item for item in reviewed if item.status == "accepted"):
        source = Path(item.operation.source).expanduser()
        destination = Path(item.operation.destination).expanduser()
        if same_path(source, destination):
            results.append(MoveResult(item.operation.id, "skipped", source, destination, "source and destination are identical")); continue
        if not source.is_file():
            results.append(MoveResult(item.operation.id, "missing", source, destination, "source does not exist")); continue
        key = canonical_path(destination)
        if key in planned_destinations or destination.exists():
            results.append(MoveResult(item.operation.id, "conflict", source, destination, "destination already exists")); continue
        planned_destinations.add(key)
        if dry_run:
            results.append(MoveResult(item.operation.id, "planned", source, destination)); continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        results.append(MoveResult(item.operation.id, "moved", source, destination))
    return tuple(results)
