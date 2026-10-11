from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from .path_safety import canonical_path
from .proposal import MoveOperation, MoveProposal


@dataclass(frozen=True, slots=True)
class FolderDecision:
    operation: MoveOperation
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class AppliedMove:
    operation_id: int
    source: str
    destination: str


def review_folder_plan(proposal: MoveProposal, *, accept_ids: set[int] | None = None, reject_ids: set[int] | None = None) -> tuple[FolderDecision, ...]:
    accepted = accept_ids or set()
    rejected = reject_ids or set()
    if accepted & rejected:
        raise ValueError("an operation cannot be both accepted and rejected")
    return tuple(FolderDecision(operation, "rejected" if operation.id in rejected else "accepted" if operation.id in accepted else "pending") for operation in proposal.operations)


def validate_folder_plan(decisions: tuple[FolderDecision, ...]) -> tuple[str, ...]:
    blockers: list[str] = []
    destinations: set[Path] = set()
    for decision in decisions:
        if decision.status != "accepted":
            continue
        source = Path(decision.operation.source).expanduser()
        destination = Path(decision.operation.destination).expanduser()
        if not source.is_file():
            blockers.append(f"#{decision.operation.id}: source is missing: {source}")
        key = canonical_path(destination)
        if key in destinations:
            blockers.append(f"#{decision.operation.id}: duplicate destination: {destination}")
        destinations.add(key)
        if destination.exists():
            blockers.append(f"#{decision.operation.id}: destination already exists: {destination}")
        if decision.operation.confidence < 0.60:
            blockers.append(f"#{decision.operation.id}: low-confidence classification ({decision.operation.confidence:.0%})")
    return tuple(blockers)


def apply_folder_plan(decisions: tuple[FolderDecision, ...], *, confirm: bool = False, journal_path: str | Path | None = None) -> tuple[AppliedMove, ...]:
    if not confirm:
        raise ValueError("filesystem changes require explicit confirmation")
    blockers = validate_folder_plan(decisions)
    if blockers:
        raise ValueError("folder plan has blockers: " + "; ".join(blockers))

    journal = Path(journal_path).expanduser() if journal_path is not None else None
    temporary_journal = journal.with_name(journal.name + ".tmp") if journal is not None else None
    if journal is not None:
        journal.parent.mkdir(parents=True, exist_ok=True)

    applied: list[AppliedMove] = []
    try:
        for decision in decisions:
            if decision.status != "accepted":
                continue
            source = Path(decision.operation.source).expanduser()
            destination = Path(decision.operation.destination).expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            applied.append(AppliedMove(decision.operation.id, str(source), str(destination)))

        if journal is not None and temporary_journal is not None:
            temporary_journal.write_text(
                json.dumps([asdict(item) for item in applied], indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_journal.replace(journal)
    except Exception as error:
        try:
            rollback_moves(tuple(applied))
        except (OSError, ValueError) as rollback_error:
            raise RuntimeError(
                f"folder operation failed ({error}); rollback was incomplete ({rollback_error})"
            ) from error
        raise
    return tuple(applied)


def rollback_moves(moves: tuple[AppliedMove, ...], *, confirm: bool = True) -> tuple[AppliedMove, ...]:
    if not confirm:
        raise ValueError("rollback requires explicit confirmation")
    restored: list[AppliedMove] = []
    for move in reversed(moves):
        source = Path(move.source)
        destination = Path(move.destination)
        if not destination.is_file():
            raise ValueError(f"cannot rollback #{move.operation_id}: destination is missing")
        if source.exists():
            raise ValueError(f"cannot rollback #{move.operation_id}: original source exists")
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destination), str(source))
        restored.append(move)
    return tuple(restored)
