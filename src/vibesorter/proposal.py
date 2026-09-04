from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .pipeline import AnalysisResult


@dataclass(frozen=True, slots=True)
class MoveOperation:
    id: int
    source: str
    destination: str
    vibe: str
    score: float
    confidence: float
    text_likelihood: float


@dataclass(frozen=True, slots=True)
class MoveProposal:
    version: int
    output_root: str
    operations: tuple[MoveOperation, ...]


def _safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]', "_", value).strip().rstrip(".")
    return value or "image"


def build_proposal(
    results: list[AnalysisResult], output_root: str | Path = "VibeSorted"
) -> MoveProposal:
    """Build a deterministic, read-only move plan from legacy analysis results."""
    root = Path(output_root)
    ordered = sorted(results, key=lambda result: str(result.path).casefold())
    used: set[str] = set()
    operations: list[MoveOperation] = []
    for index, result in enumerate(ordered, start=1):
        filename = _safe_name(result.path.name)
        destination = root / _safe_name(result.best.name) / filename
        key = destination.as_posix().casefold()
        stem, suffix = destination.stem, destination.suffix
        counter = 2
        while key in used:
            destination = destination.with_name(f"{stem} ({counter}){suffix}")
            key = destination.as_posix().casefold()
            counter += 1
        used.add(key)
        operations.append(
            MoveOperation(
                index,
                str(result.path),
                str(destination),
                result.best.name,
                round(result.best.score, 6),
                round(_confidence(result), 6),
                round(result.features.text_likelihood, 6),
            )
        )
    return MoveProposal(version=1, output_root=str(root), operations=tuple(operations))


def _confidence(result: AnalysisResult) -> float:
    from .vibes import confidence_score

    return confidence_score(result.scores)


def proposal_to_dict(proposal: MoveProposal) -> dict:
    return {
        "version": proposal.version,
        "output_root": proposal.output_root,
        "operations": [asdict(operation) for operation in proposal.operations],
    }


def proposal_from_dict(data: dict) -> MoveProposal:
    if data.get("version") not in {1, 2}:
        raise ValueError(f"Unsupported proposal version: {data.get('version')!r}")
    operations = tuple(MoveOperation(**item) for item in data.get("operations", []))
    ids = [operation.id for operation in operations]
    if ids != list(range(1, len(ids) + 1)):
        raise ValueError("Proposal operation IDs must be sequential starting at 1")
    return MoveProposal(
        version=int(data["version"]),
        output_root=str(data.get("output_root", "VibeSorted")),
        operations=operations,
    )


def proposal_to_json(proposal: MoveProposal) -> str:
    return json.dumps(proposal_to_dict(proposal), indent=2, ensure_ascii=False) + "\n"
