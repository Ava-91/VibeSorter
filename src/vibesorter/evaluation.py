from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .features import extract_features
from .vibes import VIBES, classify, confidence_score, score_vibes


@dataclass(frozen=True, slots=True)
class LabelledImage:
    path: Path
    label: str


def load_labels(path: str | Path) -> tuple[LabelledImage, ...]:
    """Load a local JSONL evaluation set with {"path": ..., "label": ...}."""
    records: list[LabelledImage] = []
    for line_number, line in enumerate(Path(path).expanduser().read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            label = str(data["label"])
            image_path = Path(data["path"]).expanduser()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid evaluation record on line {line_number}") from exc
        if label not in VIBES:
            raise ValueError(f"unknown vibe label on line {line_number}: {label}")
        records.append(LabelledImage(image_path, label))
    return tuple(records)


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    total: int
    correct: int
    accuracy: float
    per_vibe: dict[str, dict[str, float | int]]
    confusion_matrix: dict[str, dict[str, int]]


def evaluate_labels(labels: tuple[LabelledImage, ...]) -> ClassificationMetrics:
    """Evaluate the current deterministic classifier against human labels."""
    matrix = {actual: {predicted: 0 for predicted in VIBES} for actual in VIBES}
    for item in labels:
        predicted = classify(extract_features(item.path)).name
        matrix[item.label][predicted] += 1
    total = sum(sum(row.values()) for row in matrix.values())
    correct = sum(matrix[vibe][vibe] for vibe in VIBES)
    per_vibe: dict[str, dict[str, float | int]] = {}
    for vibe in VIBES:
        true_positive = matrix[vibe][vibe]
        actual = sum(matrix[vibe].values())
        predicted = sum(matrix[actual_vibe][vibe] for actual_vibe in VIBES)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        per_vibe[vibe] = {"support": actual, "precision": round(precision, 4), "recall": round(recall, 4)}
    return ClassificationMetrics(total, correct, round(correct / total, 4) if total else 0.0, per_vibe, matrix)


@dataclass(frozen=True, slots=True)
class ConfidenceObservation:
    label: str
    predicted: str
    raw_confidence: float
    correct: bool


def collect_confidence_observations(labels: tuple[LabelledImage, ...]) -> tuple[ConfidenceObservation, ...]:
    """Collect heuristic confidence and correctness for a labelled dataset."""
    observations: list[ConfidenceObservation] = []
    for item in labels:
        scores = score_vibes(extract_features(item.path))
        predicted = scores[0].name
        observations.append(ConfidenceObservation(item.label, predicted, confidence_score(scores), predicted == item.label))
    return tuple(observations)
