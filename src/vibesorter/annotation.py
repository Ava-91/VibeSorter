from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .profile import AttributeValue, ImageProfile
from .taxonomy import ATTRIBUTE_FAMILIES, TAXONOMY_VERSION


@dataclass(frozen=True, slots=True)
class ImageAnnotation:
    path: Path
    profile: ImageProfile
    source: str = "human"

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path.resolve()),
            "profile": self.profile.to_dict(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImageAnnotation:
        return cls(
            Path(data["path"]).expanduser().resolve(),
            ImageProfile.from_dict(data["profile"]),
            str(data.get("source", "human")),
        )


def validate_annotation(profile: ImageProfile) -> None:
    """Validate reviewer output against the current taxonomy contract."""
    if profile.taxonomy_version != TAXONOMY_VERSION:
        raise ValueError("annotation uses an unsupported taxonomy version")
    for family in ATTRIBUTE_FAMILIES:
        value = getattr(profile, family)
        if family in {"colors", "vibes"}:
            if any(not isinstance(item, AttributeValue) for item in value):
                raise ValueError(f"invalid values in {family}")
        elif value is not None and not isinstance(value, AttributeValue):
            raise ValueError(f"invalid value in {family}")


def save_annotation(output: str | Path, annotation: ImageAnnotation) -> None:
    validate_annotation(annotation.profile)
    destination = Path(output).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    records: dict[str, dict[str, Any]] = {}
    if destination.exists():
        for line in destination.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing = json.loads(line)
            records[str(Path(existing["path"]).expanduser().resolve())] = existing
    record = annotation.to_dict()
    records[record["path"]] = record
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for path in sorted(records, key=str.casefold):
            handle.write(json.dumps(records[path], ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(destination)


def load_annotations(output: str | Path) -> dict[str, ImageAnnotation]:
    path = Path(output).expanduser()
    if not path.exists():
        return {}
    result: dict[str, ImageAnnotation] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            annotation = ImageAnnotation.from_dict(json.loads(line))
            validate_annotation(annotation.profile)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid annotation on line {line_number}") from exc
        result[str(annotation.path)] = annotation
    return result
