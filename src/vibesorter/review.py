from __future__ import annotations

from dataclasses import dataclass

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
