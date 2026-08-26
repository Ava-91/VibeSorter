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
    return tuple(
        ConfidenceObservation(item.label, scores[0].name, confidence_score(scores), scores[0].name == item.label)
        for item in labels
        for scores in (score_vibes(extract_features(item.path)),)
    )


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_confidence: float
    accuracy: float


class ConfidenceCalibrator:
    """Fit an empirical confidence correction from labelled observations."""

    def __init__(self, bins: int = 10) -> None:
        if bins < 1:
            raise ValueError("bins must be at least 1")
        self.bins = bins
        self._calibration: tuple[CalibrationBin, ...] = ()

    def fit(self, observations: tuple[ConfidenceObservation, ...]) -> "ConfidenceCalibrator":
        width = 1.0 / self.bins
        fitted: list[CalibrationBin] = []
        for index in range(self.bins):
            lower = index * width
            upper = 1.0 if index == self.bins - 1 else (index + 1) * width
            bucket = [item for item in observations if lower <= item.raw_confidence < upper or (upper == 1.0 and item.raw_confidence <= upper)]
            if not bucket:
                fitted.append(CalibrationBin(lower, upper, 0, 0.0, 0.0))
                continue
            mean = sum(item.raw_confidence for item in bucket) / len(bucket)
            accuracy = sum(item.correct for item in bucket) / len(bucket)
            fitted.append(CalibrationBin(lower, upper, len(bucket), round(mean, 4), round(accuracy, 4)))
        self._calibration = tuple(fitted)
        return self

    @property
    def bins_report(self) -> tuple[CalibrationBin, ...]:
        return self._calibration

    def transform(self, confidence: float) -> float:
        """Map a raw confidence to empirical observed accuracy."""
        value = max(0.0, min(1.0, confidence))
        if not self._calibration:
            return value
        for item in self._calibration:
            if item.count and item.lower <= value < item.upper:
                return item.accuracy
        populated = [item for item in self._calibration if item.count]
        return populated[-1].accuracy if populated else value
