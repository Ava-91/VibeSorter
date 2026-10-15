from __future__ import annotations

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


def apply_reviewed(
    reviewed: tuple[ReviewedOperation, ...],
    *,
    confirm: bool = False,
    dry_run: bool = False,
    source_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> tuple[MoveResult, ...]:
    """Apply accepted moves only after validating the entire batch's path boundaries."""
    if not confirm and not dry_run:
        raise ValueError("filesystem changes require explicit confirmation")
    accepted = tuple(item for item in reviewed if item.status == "accepted")
    if not accepted:
        return ()

    # A single unsafe item blocks the entire batch before any filesystem changes.
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

    results: list[MoveResult] = []
    planned_destinations: set[Path] = set()
    for item in accepted:
        source = Path(item.operation.source).expanduser()
        destination = Path(item.operation.destination).expanduser()
        if item.operation.confidence < MIN_APPLY_CONFIDENCE:
            results.append(MoveResult(
                item.operation.id, "low_confidence", source, destination,
                f"classification confidence {item.operation.confidence:.0%} is below the {MIN_APPLY_CONFIDENCE:.0%} apply threshold",
            ))
            continue
        key = canonical_path(destination)
        if key in planned_destinations or destination.exists():
            results.append(MoveResult(item.operation.id, "conflict", source, destination, "destination already exists"))
            continue
        planned_destinations.add(key)
        if dry_run:
            results.append(MoveResult(item.operation.id, "planned", source, destination))
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Recheck containment after directory creation before mutating the source.
        if not is_within(destination.resolve(strict=False), Path(output_root).expanduser().resolve(strict=False), allow_root=False):
            raise ValueError(f"destination escaped output_root during apply: {destination}")
        shutil.move(str(source), str(destination))
        results.append(MoveResult(item.operation.id, "moved", source, destination))
    return tuple(results)
