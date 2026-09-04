from __future__ import annotations

import re
from pathlib import Path

from .pipeline import AnalysisResult
from .profile import ImageProfile
from .proposal import MoveOperation, MoveProposal
from .taxonomy import ATTRIBUTE_CARDINALITY

FOLDERABLE_FAMILIES = tuple(ATTRIBUTE_CARDINALITY)


def _safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*]', "_", value).strip().rstrip(".")
    return value or "Unclassified"


def _folder_value(profile: ImageProfile | None, family: str) -> str:
    if family not in FOLDERABLE_FAMILIES:
        raise ValueError(f"unknown folder attribute: {family}")
    if profile is None:
        return "Unclassified"
    value = getattr(profile, family)
    if isinstance(value, tuple):
        value = max(value, key=lambda item: item.confidence, default=None)
    return _safe_name(value.value) if value else "Unclassified"


def build_attribute_proposal(
    results: list[AnalysisResult],
    profiles: dict[str | Path, ImageProfile | None],
    output_root: str | Path = "VibeSorted",
    *,
    primary_attribute: str = "media_type",
) -> MoveProposal:
    """Build a deterministic, read-only folder plan from image profiles."""
    if primary_attribute not in FOLDERABLE_FAMILIES:
        raise ValueError(f"unknown folder attribute: {primary_attribute}")
    root = Path(output_root)
    ordered = sorted(results, key=lambda result: str(result.path).casefold())
    used: set[str] = set()
    operations: list[MoveOperation] = []
    for index, result in enumerate(ordered, start=1):
        profile = profiles.get(result.path, profiles.get(str(result.path)))
        folder = _folder_value(profile, primary_attribute)
        destination = root / folder / _safe_name(result.path.name)
        key = destination.as_posix().casefold()
        stem, suffix = destination.stem, destination.suffix
        counter = 2
        while key in used:
            destination = destination.with_name(f"{stem} ({counter}){suffix}")
            key = destination.as_posix().casefold()
            counter += 1
        used.add(key)
        confidence = _folder_confidence(profile, primary_attribute)
        operations.append(
            MoveOperation(
                id=index,
                source=str(result.path),
                destination=str(destination),
                vibe=folder,
                score=round(confidence, 6),
                confidence=round(confidence, 6),
                text_likelihood=round(result.features.text_likelihood, 6),
            )
        )
    return MoveProposal(version=2, output_root=str(root), operations=tuple(operations))


def _folder_confidence(profile: ImageProfile | None, family: str) -> float:
    if profile is None:
        return 0.0
    value = getattr(profile, family)
    if isinstance(value, tuple):
        return max((item.confidence for item in value), default=0.0)
    return value.confidence if value is not None else 0.0
