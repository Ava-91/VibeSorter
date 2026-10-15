from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .path_safety import canonical_path, has_traversal, is_within, same_path
from .review import ReviewedOperation

MIN_APPLY_CONFIDENCE = 0.60


@dataclass(frozen=True, slots=True)
class MoveResult:
    operation_id: int
    status: str
    source: Path
    destination: Path
    detail: str = ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _journal_move(journal_path: Path, batch_id: str, result: MoveResult) -> None:
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event": "move",
        "batch_id": batch_id,
        "operation_id": result.operation_id,
        "source": str(result.source),
        "destination": str(result.destination),
        "sha256": _sha256(result.destination),
    }
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _rollback_moves(moved: list[MoveResult]) -> list[str]:
    failures: list[str] = []
    for result in reversed(moved):
        if not result.destination.is_file():
            failures.append(f"#{result.operation_id}: destination missing at {result.destination}")
            continue
        if result.source.exists():
            failures.append(f"#{result.operation_id}: source path occupied at {result.source}")
            continue
        try:
            result.source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(result.destination), str(result.source))
        except OSError as exc:
            failures.append(f"#{result.operation_id}: {exc}")
    return failures


def apply_reviewed(
    reviewed: tuple[ReviewedOperation, ...],
    *,
    confirm: bool = False,
    dry_run: bool = False,
    source_root: str | Path | None = None,
    output_root: str | Path | None = None,
    journal_path: str | Path | None = None,
    batch_id: str = "",
) -> tuple[MoveResult, ...]:
    """Validate, journal, and apply accepted moves as one recoverable batch."""
    if not confirm and not dry_run:
        raise ValueError("filesystem changes require explicit confirmation")
    accepted = tuple(item for item in reviewed if item.status == "accepted")
    if not accepted:
        return ()

    try:
        if not source_root or not output_root:
            raise ValueError("proposal is missing its source_root or output_root safety boundary")
        source_base = Path(source_root).expanduser().resolve(strict=True)
        if not source_base.is_dir():
            raise ValueError("source_root is not a directory")
        output_base = Path(output_root).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        return tuple(
            MoveResult(item.operation.id, "unsafe_path", Path(item.operation.source),
                       Path(item.operation.destination), str(exc))
            for item in accepted
        )

    errors: dict[int, str] = {}
    destinations: dict[Path, int] = {}
    for item in accepted:
        op = item.operation
        source, destination = Path(op.source).expanduser(), Path(op.destination).expanduser()
        error = None
        if has_traversal(op.source) or has_traversal(op.destination):
            error = "paths must not contain parent-directory traversal"
        elif source.is_symlink():
            error = "source must not be a symbolic link"
        else:
            try:
                resolved_source = source.resolve(strict=True)
                resolved_destination = destination.resolve(strict=False)
            except (OSError, RuntimeError) as exc:
                error = f"path could not be resolved safely: {exc}"
            else:
                if not is_within(resolved_source, source_base, allow_root=False):
                    error = "source is outside the selected library root"
                elif not resolved_source.is_file():
                    error = "source is not a regular file"
                elif not is_within(resolved_destination, output_base, allow_root=False):
                    error = "destination is outside the selected output root"
                elif same_path(resolved_source, resolved_destination):
                    error = "source and destination are identical"
                else:
                    key = canonical_path(resolved_destination)
                    if key in destinations:
                        previous_id = destinations[key]
                        errors[previous_id] = f"destination duplicates operation {op.id}"
                        error = f"destination duplicates operation {previous_id}"
                    else:
                        destinations[key] = op.id
        if error:
            errors[op.id] = error

    if errors:
        return tuple(
            MoveResult(item.operation.id,
                       "unsafe_path" if item.operation.id in errors else "blocked",
                       Path(item.operation.source).expanduser(),
                       Path(item.operation.destination).expanduser(),
                       errors.get(item.operation.id, "batch blocked because another operation has an unsafe path"))
            for item in accepted
        )

    plan: list[MoveResult] = []
    planned_destinations: set[Path] = set()
    for item in accepted:
        source, destination = Path(item.operation.source).expanduser(), Path(item.operation.destination).expanduser()
        if item.operation.confidence < MIN_APPLY_CONFIDENCE:
            plan.append(MoveResult(item.operation.id, "low_confidence", source, destination,
                                   f"classification confidence {item.operation.confidence:.0%} is below the {MIN_APPLY_CONFIDENCE:.0%} apply threshold"))
            continue
        key = canonical_path(destination)
        if key in planned_destinations or destination.exists():
            plan.append(MoveResult(item.operation.id, "conflict", source, destination, "destination already exists"))
            continue
        planned_destinations.add(key)
        plan.append(MoveResult(item.operation.id, "planned" if dry_run else "ready", source, destination))

    if dry_run:
        return tuple(plan)

    journal = Path(journal_path).expanduser() if journal_path is not None else None
    if journal is not None:
        journal.parent.mkdir(parents=True, exist_ok=True)
    moved: list[MoveResult] = []
    try:
        for planned in plan:
            if planned.status != "ready":
                continue
            if planned.destination.exists():
                raise FileExistsError(f"destination appeared during apply: {planned.destination}")
            planned.destination.parent.mkdir(parents=True, exist_ok=True)
            if not is_within(planned.destination.resolve(strict=False), output_base, allow_root=False):
                raise ValueError(f"destination escaped output_root during apply: {planned.destination}")
            shutil.move(str(planned.source), str(planned.destination))
            result = MoveResult(planned.operation_id, "moved", planned.source, planned.destination)
            moved.append(result)
            if journal is not None:
                _journal_move(journal, batch_id, result)
    except Exception as exc:
        failures = _rollback_moves(moved)
        if journal is not None and not failures:
            try:
                journal.unlink(missing_ok=True)
            except OSError as cleanup_error:
                failures.append(f"could not remove completed recovery journal {journal}: {cleanup_error}")
        detail = f"batch apply failed: {exc}"
        if failures:
            detail += "; rollback incomplete: " + "; ".join(failures)
            if journal is not None:
                detail += f"; recovery journal preserved at {journal}"
        raise OSError(detail) from exc

    moved_by_id = {result.operation_id: result for result in moved}
    return tuple(moved_by_id.get(item.operation.id, MoveResult(
        item.operation.id,
        "low_confidence" if item.operation.confidence < MIN_APPLY_CONFIDENCE else "conflict",
        Path(item.operation.source).expanduser(),
        Path(item.operation.destination).expanduser(),
        f"classification confidence {item.operation.confidence:.0%} is below the {MIN_APPLY_CONFIDENCE:.0%} apply threshold" if item.operation.confidence < MIN_APPLY_CONFIDENCE else "destination already exists",
    )) for item in accepted)
