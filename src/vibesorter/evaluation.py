from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .features import extract_features
from .vibes import VIBES, classify, confidence_score, is_confident, score_vibes


@dataclass(frozen=True, slots=True)
class LabelledImage:
    path: Path
    label: str


def load_labels(path: str | Path) -> tuple[LabelledImage, ...]:
    records = []
    for line_number, line in enumerate(
        Path(path).expanduser().read_text(encoding="utf-8").splitlines(), start=1
    ):
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

    def to_dict(self) -> dict:
        return asdict(self)


def _metrics(labels: tuple[LabelledImage, ...], predictor) -> ClassificationMetrics:
    matrix = {actual: {predicted: 0 for predicted in VIBES} for actual in VIBES}
    for item in labels:
        matrix[item.label][predictor(item).name] += 1

    total = sum(sum(row.values()) for row in matrix.values())
    correct = sum(matrix[vibe][vibe] for vibe in VIBES)
    per_vibe = {}
    for vibe in VIBES:
        tp = matrix[vibe][vibe]
        actual = sum(matrix[vibe].values())
        predicted = sum(matrix[actual_vibe][vibe] for actual_vibe in VIBES)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        per_vibe[vibe] = {
            "support": actual,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    return ClassificationMetrics(
        total,
        correct,
        round(correct / total, 4) if total else 0.0,
        per_vibe,
        matrix,
    )


def evaluate_labels(labels: tuple[LabelledImage, ...]) -> ClassificationMetrics:
    """Evaluate the deterministic heuristic classifier against human labels."""
    return _metrics(labels, lambda item: classify(extract_features(item.path)))


def evaluate_classifier(labels: tuple[LabelledImage, ...], classifier) -> ClassificationMetrics:
    """Evaluate any classifier exposing ``predict(path)`` against the same labels."""
    return _metrics(labels, classifier.predict)


@dataclass(frozen=True, slots=True)
class ConfidenceObservation:
    label: str
    predicted: str
    raw_confidence: float
    correct: bool
    confident: bool


def collect_confidence_observations(
    labels: tuple[LabelledImage, ...],
) -> tuple[ConfidenceObservation, ...]:
    observations = []
    for item in labels:
        scores = score_vibes(extract_features(item.path))
        observations.append(
            ConfidenceObservation(
                item.label,
                scores[0].name,
                confidence_score(scores),
                scores[0].name == item.label,
                is_confident(scores),
            )
        )
    return tuple(observations)


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_confidence: float
    accuracy: float


class ConfidenceCalibrator:
    def __init__(self, bins: int = 10) -> None:
        if bins < 1:
            raise ValueError("bins must be at least 1")
        self.bins = bins
        self._calibration = ()

    def fit(self, observations: tuple[ConfidenceObservation, ...]) -> "ConfidenceCalibrator":
        width = 1.0 / self.bins
        fitted = []
        for index in range(self.bins):
            lower = index * width
            upper = 1.0 if index == self.bins - 1 else (index + 1) * width
            bucket = [
                item
                for item in observations
                if lower <= item.raw_confidence < upper
                or (upper == 1.0 and item.raw_confidence <= upper)
            ]
            fitted.append(
                CalibrationBin(
                    lower,
                    upper,
                    len(bucket),
                    round(sum(x.raw_confidence for x in bucket) / len(bucket), 4)
                    if bucket
                    else 0.0,
                    round(sum(x.correct for x in bucket) / len(bucket), 4)
                    if bucket
                    else 0.0,
                )
            )
        self._calibration = tuple(fitted)
        return self

    @property
    def bins_report(self):
        return self._calibration

    def transform(self, confidence: float) -> float:
        value = max(0.0, min(1.0, confidence))
        for item in self._calibration:
            if item.count and item.lower <= value < item.upper:
                return item.accuracy
        populated = [item for item in self._calibration if item.count]
        return populated[-1].accuracy if populated else value

    def report(self):
        return [asdict(item) for item in self._calibration]


def expected_calibration_error(
    observations: tuple[ConfidenceObservation, ...], bins: int = 10
) -> float:
    """Return confidence-weighted calibration error for the labelled set."""
    if bins < 1:
        raise ValueError("bins must be at least 1")
    if not observations:
        return 0.0
    calibrator = ConfidenceCalibrator(bins).fit(observations)
    total = len(observations)
    return round(
        sum(
            item.count * abs(item.mean_confidence - item.accuracy)
            for item in calibrator.bins_report
        )
        / total,
        4,
    )


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    metrics: ClassificationMetrics
    labelled_images: int
    ambiguous: int
    ambiguous_rate: float
    confidence_error: float
    calibration: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_dataset(
    labels: tuple[LabelledImage, ...], *, bins: int = 10
) -> EvaluationReport:
    """Build a complete read-only report for a human-labelled image set."""
    observations = collect_confidence_observations(labels)
    calibrator = ConfidenceCalibrator(bins).fit(observations)
    ambiguous = sum(not item.confident for item in observations)
    return EvaluationReport(
        metrics=evaluate_labels(labels),
        labelled_images=len(labels),
        ambiguous=ambiguous,
        ambiguous_rate=round(ambiguous / len(labels), 4) if labels else 0.0,
        confidence_error=expected_calibration_error(observations, bins),
        calibration=calibrator.report(),
    )
