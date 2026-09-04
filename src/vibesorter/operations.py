from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .review import ReviewedOperation


@dataclass(frozen=True, slots=True)
class MoveResult:
    operation_id: int
    status: str
    source: Path
    destination: Path
    detail: str = ""


def apply_reviewed(
    reviewed: tuple[ReviewedOperation, ...],
    *,
    confirm: bool = False,
    dry_run: bool = False,
) -> tuple[MoveResult, ...]:
    """Apply only explicitly accepted operations.

    This is the only module that mutates user files. A real run requires
    ``confirm=True``; destinations are never overwritten silently.
    """
    if not confirm and not dry_run:
        raise ValueError("filesystem changes require explicit confirmation")

    results: list[MoveResult] = []
    accepted = [item for item in reviewed if item.status == "accepted"]
    planned_destinations: set[Path] = set()

    for item in accepted:
        source = Path(item.operation.source).expanduser()
        destination = Path(item.operation.destination).expanduser()
        if source.resolve() == destination.resolve():
            results.append(MoveResult(item.operation.id, "skipped", source, destination, "source and destination are identical"))
            continue
        if not source.is_file():
            results.append(MoveResult(item.operation.id, "missing", source, destination, "source does not exist"))
            continue
        if destination in planned_destinations or destination.exists():
            results.append(MoveResult(item.operation.id, "conflict", source, destination, "destination already exists"))
            continue
        planned_destinations.add(destination)
        if dry_run:
            results.append(MoveResult(item.operation.id, "planned", source, destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        results.append(MoveResult(item.operation.id, "moved", source, destination))

    return tuple(results)
