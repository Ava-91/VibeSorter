from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .proposal import MoveOperation, MoveProposal


@dataclass(frozen=True, slots=True)
class ReviewedOperation:
    operation: MoveOperation
    status: str


def parse_selection(value: str, max_id: int) -> set[int]:
    """Parse IDs/ranges such as '1,3-5' or the special value 'all'."""
    value = value.strip().lower()
    if not value:
        return set()
    if value == "all":
        return set(range(1, max_id + 1))
    selected: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
            start, end = int(left), int(right)
            if start > end:
                raise ValueError(f"Invalid range: {token}")
            selected.update(range(start, end + 1))
        else:
            selected.add(int(token))
    invalid = sorted(item for item in selected if item < 1 or item > max_id)
    if invalid:
        raise ValueError(f"Operation ID out of range: {invalid[0]}")
    return selected


def review_proposal(
    proposal: MoveProposal,
    *,
    accept_ids: set[int] | None = None,
    reject_ids: set[int] | None = None,
    accept_vibes: set[str] | None = None,
    reject_vibes: set[str] | None = None,
) -> tuple[ReviewedOperation, ...]:
    accept_ids = accept_ids or set()
    reject_ids = reject_ids or set()
    accept_vibes = accept_vibes or set()
    reject_vibes = reject_vibes or set()
    reviewed = []
    for operation in proposal.operations:
        if operation.id in reject_ids or operation.vibe in reject_vibes:
            status = "rejected"
        elif operation.id in accept_ids or operation.vibe in accept_vibes:
            status = "accepted"
        else:
            status = "pending"
        reviewed.append(ReviewedOperation(operation=operation, status=status))
    return tuple(reviewed)


def reviewed_to_dict(
    proposal: MoveProposal, reviewed: tuple[ReviewedOperation, ...]
) -> dict:
    """Serialize a proposal together with its review decisions."""
    if len(proposal.operations) != len(reviewed):
        raise ValueError("reviewed operations must match the proposal operations")
    if tuple(item.operation for item in reviewed) != proposal.operations:
        raise ValueError("reviewed operations must preserve proposal order")
    return {
        "version": proposal.version,
        "output_root": proposal.output_root,
        "operations": [asdict(operation) for operation in proposal.operations],
        "review": [
            {"id": item.operation.id, "status": item.status} for item in reviewed
        ],
    }


def reviewed_to_json(
    proposal: MoveProposal, reviewed: tuple[ReviewedOperation, ...]
) -> str:
    return json.dumps(reviewed_to_dict(proposal, reviewed), indent=2, ensure_ascii=False) + "\n"


def reviewed_from_dict(data: dict) -> tuple[ReviewedOperation, ...]:
    """Deserialize the reviewed decisions from a proposal JSON document."""
    if not isinstance(data, dict) or not isinstance(data.get("review"), list):
        raise ValueError("reviewed proposal must contain a review list")
    from .proposal import proposal_from_dict

    proposal_data = {key: value for key, value in data.items() if key != "review"}
    proposal = proposal_from_dict(proposal_data)
    review = data["review"]
    if len(review) != len(proposal.operations):
        raise ValueError("review must contain one decision per proposal operation")
    by_id: dict[int, str] = {}
    for item in review:
        if not isinstance(item, dict):
            raise ValueError("review entries must be objects")
        operation_id = item.get("id")
        status = item.get("status")
        if not isinstance(operation_id, int):
            raise ValueError("review operation IDs must be integers")
        if status not in {"pending", "accepted", "rejected"}:
            raise ValueError(f"Unsupported review status: {status!r}")
        if operation_id in by_id:
            raise ValueError(f"Duplicate review operation ID: {operation_id}")
        by_id[operation_id] = status
    expected_ids = {operation.id for operation in proposal.operations}
    if set(by_id) != expected_ids:
        raise ValueError("review operation IDs must match proposal operation IDs")
    return tuple(
        ReviewedOperation(operation, by_id[operation.id])
        for operation in proposal.operations
    )
