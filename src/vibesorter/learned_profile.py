from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .annotation import ImageAnnotation
from .features import ImageFeatures, extract_features
from .learned import feature_vector
from .profile import AttributeValue, ImageProfile
from .taxonomy import ATTRIBUTE_FAMILIES

MODEL_VERSION = 2
MULTI_FAMILY = {"colors", "vibes"}


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    size = min(len(left), len(right))
    return math.sqrt(sum((left[i] - right[i]) ** 2 for i in range(size)))


def _values(profile: ImageProfile, family: str) -> tuple[str, ...]:
    value = getattr(profile, family)
    if family in MULTI_FAMILY:
        return tuple(item.value for item in value)
    return (value.value,) if value is not None else ()


@dataclass(frozen=True, slots=True)
class LearnedProfileClassifier:
    centroids: dict[str, dict[str, tuple[float, ...]]]
    samples: dict[str, dict[str, int]]

    @classmethod
    def fit(cls, annotations: tuple[ImageAnnotation, ...]) -> LearnedProfileClassifier:
        if not annotations:
            raise ValueError("training dataset contains no annotations")
        grouped: dict[str, dict[str, list[tuple[float, ...]]]] = {family: {} for family in ATTRIBUTE_FAMILIES}
        for annotation in annotations:
            vector = feature_vector(extract_features(annotation.path))
            for family in ATTRIBUTE_FAMILIES:
                for value in _values(annotation.profile, family):
                    grouped[family].setdefault(value, []).append(vector)
        centroids: dict[str, dict[str, tuple[float, ...]]] = {}
        samples: dict[str, dict[str, int]] = {}
        for family, values in grouped.items():
            centroids[family], samples[family] = {}, {}
            for value, vectors in values.items():
                width = max(map(len, vectors))
                centroids[family][value] = tuple(
                    sum(vector[i] if i < len(vector) else 0.0 for vector in vectors) / len(vectors)
                    for i in range(width)
                )
                samples[family][value] = len(vectors)
        if not any(centroids.values()):
            raise ValueError("training dataset contains no usable attributes")
        return cls(centroids, samples)

    def predict_features(self, features: ImageFeatures) -> ImageProfile:
        vector = feature_vector(features)

        def one(family: str) -> AttributeValue | None:
            scores = self._scores(family, vector)
            if not scores:
                return None
            value, confidence = scores[0]
            return AttributeValue(value, confidence, "learned")

        def many(family: str) -> tuple[AttributeValue, ...]:
            return tuple(
                AttributeValue(value, confidence, "learned")
                for value, confidence in self._scores(family, vector)
                if confidence >= 0.35
            )

        return ImageProfile(
            media_type=one("media_type"), colors=many("colors"), temperature=one("temperature"),
            saturation=one("saturation"), brightness=one("brightness"), vibes=many("vibes"),
        )

    def _scores(self, family: str, vector: tuple[float, ...]) -> tuple[tuple[str, float], ...]:
        candidates = self.centroids.get(family, {})
        similarities = {value: 1.0 / (1.0 + _distance(vector, centroid)) for value, centroid in candidates.items()}
        if not similarities:
            return ()
        total = sum(similarities.values()) or 1.0
        return tuple(sorted(((value, round(score / total, 4)) for value, score in similarities.items()), key=lambda item: item[1], reverse=True))

    def predict(self, path: str | Path) -> ImageProfile:
        return self.predict_features(extract_features(path))

    def save(self, path: str | Path) -> None:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"version": MODEL_VERSION, "centroids": self.centroids, "samples": self.samples}, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> LearnedProfileClassifier:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if data.get("version") != MODEL_VERSION:
            raise ValueError("unsupported learned profile classifier model version")
        centroids = {str(family): {str(value): tuple(float(x) for x in vector) for value, vector in values.items()} for family, values in data["centroids"].items()}
        samples = {str(family): {str(value): int(count) for value, count in values.items()} for family, values in data.get("samples", {}).items()}
        return cls(centroids, samples)
