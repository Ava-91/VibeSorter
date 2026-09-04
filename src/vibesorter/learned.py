from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from .evaluation import LabelledImage
from .features import ImageFeatures, extract_features
from .taxonomy import Vibe
from .vibes import VibeScore

MODEL_VERSION = 2
CANONICAL_VIBES = tuple(item.value for item in Vibe)


def feature_vector(features: ImageFeatures) -> tuple[float, ...]:
    values = [
        features.brightness,
        features.saturation,
        features.contrast,
        features.warm_ratio,
        features.cool_ratio,
        features.grayscale_ratio,
        features.dark_ratio,
        features.light_ratio,
        features.text_likelihood,
        features.center_brightness_delta,
        features.center_saturation_delta,
    ]
    for region in features.regions:
        values.extend((region.brightness, region.saturation, region.warm_ratio, region.cool_ratio))
    return tuple(values)


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    size = min(len(left), len(right))
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(size)))


@dataclass(frozen=True, slots=True)
class LearnedClassifier:
    centroids: dict[str, tuple[float, ...]]
    samples: dict[str, int]

    @classmethod
    def fit(cls, labels: tuple[LabelledImage, ...]) -> LearnedClassifier:
        grouped: dict[str, list[tuple[float, ...]]] = {vibe: [] for vibe in CANONICAL_VIBES}
        for item in labels:
            grouped[item.label].append(feature_vector(extract_features(item.path)))
        centroids: dict[str, tuple[float, ...]] = {}
        samples: dict[str, int] = {}
        for vibe, vectors in grouped.items():
            if not vectors:
                continue
            width = max(len(vector) for vector in vectors)
            centroids[vibe] = tuple(
                sum(vector[index] if index < len(vector) else 0.0 for vector in vectors) / len(vectors)
                for index in range(width)
            )
            samples[vibe] = len(vectors)
        if not centroids:
            raise ValueError("training dataset contains no usable labelled images")
        return cls(centroids, samples)

    def score(self, features: ImageFeatures) -> tuple[VibeScore, ...]:
        vector = feature_vector(features)
        distances = {vibe: _distance(vector, centroid) for vibe, centroid in self.centroids.items()}
        similarities = {vibe: 1.0 / (1.0 + distance) for vibe, distance in distances.items()}
        total = sum(similarities.values()) or 1.0
        scores = [VibeScore(vibe, round(value / total, 4)) for vibe, value in similarities.items()]
        return tuple(sorted(scores, key=lambda item: item.score, reverse=True))

    def predict(self, path: str | Path) -> VibeScore:
        return self.score(extract_features(path))[0]

    def save(self, path: str | Path) -> None:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {"version": MODEL_VERSION, "centroids": self.centroids, "samples": self.samples},
                indent=2,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> LearnedClassifier:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if data.get("version") != MODEL_VERSION:
            raise ValueError("unsupported learned classifier model version")
        centroids = {
            str(name): tuple(float(value) for value in values)
            for name, values in data["centroids"].items()
        }
        if any(name not in CANONICAL_VIBES for name in centroids):
            raise ValueError("learned classifier contains non-canonical vibe labels")
        return cls(
            centroids,
            {str(name): int(value) for name, value in data.get("samples", {}).items()},
        )
