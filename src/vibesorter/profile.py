from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .taxonomy import TAXONOMY_VERSION, ATTRIBUTE_FAMILIES, is_legacy_label


@dataclass(frozen=True, slots=True)
class AttributeValue:
    value: str
    confidence: float
    source: str = "classifier"

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("attribute value must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("attribute confidence must be between 0 and 1")
        if not self.source:
            raise ValueError("attribute source must not be empty")
        if is_legacy_label(self.value):
            raise ValueError(f"legacy compound label is not valid: {self.value}")


@dataclass(frozen=True, slots=True)
class ImageProfile:
    media_type: AttributeValue | None = None
    colors: tuple[AttributeValue, ...] = field(default_factory=tuple)
    temperature: AttributeValue | None = None
    saturation: AttributeValue | None = None
    brightness: AttributeValue | None = None
    vibes: tuple[AttributeValue, ...] = field(default_factory=tuple)
    taxonomy_version: str = TAXONOMY_VERSION

    def __post_init__(self) -> None:
        if self.taxonomy_version != TAXONOMY_VERSION:
            raise ValueError(f"unsupported taxonomy version: {self.taxonomy_version}")
        self._validate_multi(self.colors, "colors")
        self._validate_multi(self.vibes, "vibes")

    @staticmethod
    def _validate_multi(values: tuple[AttributeValue, ...], family: str) -> None:
        if family not in ATTRIBUTE_FAMILIES:
            raise ValueError(f"unknown attribute family: {family}")
        seen: set[str] = set()
        for item in values:
            if item.value in seen:
                raise ValueError(f"duplicate {family} value: {item.value}")
            seen.add(item.value)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["media_type"] = asdict(self.media_type) if self.media_type else None
        for family in ("colors", "vibes"):
            data[family] = [asdict(item) for item in getattr(self, family)]
        for family in ("temperature", "saturation", "brightness"):
            value = getattr(self, family)
            data[family] = asdict(value) if value else None
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImageProfile:
        def one(name: str) -> AttributeValue | None:
            value = data.get(name)
            return AttributeValue(**value) if value else None

        def many(name: str) -> tuple[AttributeValue, ...]:
            return tuple(AttributeValue(**value) for value in data.get(name, []))

        return cls(
            media_type=one("media_type"),
            colors=many("colors"),
            temperature=one("temperature"),
            saturation=one("saturation"),
            brightness=one("brightness"),
            vibes=many("vibes"),
            taxonomy_version=data.get("taxonomy_version", TAXONOMY_VERSION),
        )

    @classmethod
    def from_json(cls, payload: str) -> ImageProfile:
        return cls.from_dict(json.loads(payload))
