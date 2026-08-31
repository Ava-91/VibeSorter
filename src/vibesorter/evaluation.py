from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .features import extract_features
from .vibes import VIBES, classify, confidence_score, score_vibes

@dataclass(frozen=True, slots=True)
class LabelledImage:
    path: Path
    label: str

def load_labels(path: str | Path) -> tuple[LabelledImage, ...]:
    records = []
    for line_number, line in enumerate(Path(path).expanduser().read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip(): continue
        try:
            data = json.loads(line); label = str(data["label"]); image_path = Path(data["path"]).expanduser()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc: raise ValueError(f"invalid evaluation record on line {line_number}") from exc
        if label not in VIBES: raise ValueError(f"unknown vibe label on line {line_number}: {label}")
        records.append(LabelledImage(image_path, label))
    return tuple(records)

@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    total: int; correct: int; accuracy: float; per_vibe: dict[str, dict[str, float | int]]; confusion_matrix: dict[str, dict[str, int]]
    def to_dict(self) -> dict: return asdict(self)

def _metrics(labels: tuple[LabelledImage, ...], predictor) -> ClassificationMetrics:
    matrix = {actual: {predicted: 0 for predicted in VIBES} for actual in VIBES}
    for item in labels: matrix[item.label][predictor(item).name] += 1
    total = sum(sum(row.values()) for row in matrix.values()); correct = sum(matrix[v][v] for v in VIBES)
    per_vibe = {}
    for vibe in VIBES:
        tp = matrix[vibe][vibe]; actual = sum(matrix[vibe].values()); predicted = sum(matrix[a][vibe] for a in VIBES)
        per_vibe[vibe] = {"support": actual, "precision": round(tp/predicted, 4) if predicted else 0.0, "recall": round(tp/actual, 4) if actual else 0.0}
    return ClassificationMetrics(total, correct, round(correct/total, 4) if total else 0.0, per_vibe, matrix)

def evaluate_labels(labels: tuple[LabelledImage, ...]) -> ClassificationMetrics:
    """Evaluate the deterministic heuristic classifier against human labels."""
    return _metrics(labels, lambda item: classify(extract_features(item.path)))

def evaluate_classifier(labels: tuple[LabelledImage, ...], classifier) -> ClassificationMetrics:
    """Evaluate any classifier exposing ``predict(path)`` against the same labels."""
    return _metrics(labels, classifier.predict)

@dataclass(frozen=True, slots=True)
class ConfidenceObservation:
    label: str; predicted: str; raw_confidence: float; correct: bool

def collect_confidence_observations(labels: tuple[LabelledImage, ...]) -> tuple[ConfidenceObservation, ...]:
    return tuple(ConfidenceObservation(item.label, scores[0].name, confidence_score(scores), scores[0].name == item.label) for item in labels for scores in (score_vibes(extract_features(item.path)),))

@dataclass(frozen=True, slots=True)
class CalibrationBin:
    lower: float; upper: float; count: int; mean_confidence: float; accuracy: float

class ConfidenceCalibrator:
    def __init__(self, bins: int = 10) -> None:
        if bins < 1: raise ValueError("bins must be at least 1")
        self.bins = bins; self._calibration = ()
    def fit(self, observations: tuple[ConfidenceObservation, ...]) -> "ConfidenceCalibrator":
        width = 1.0 / self.bins; fitted = []
        for index in range(self.bins):
            lower = index*width; upper = 1.0 if index == self.bins-1 else (index+1)*width
            bucket = [item for item in observations if lower <= item.raw_confidence < upper or (upper == 1.0 and item.raw_confidence <= upper)]
            fitted.append(CalibrationBin(lower, upper, len(bucket), round(sum(x.raw_confidence for x in bucket)/len(bucket), 4) if bucket else 0.0, round(sum(x.correct for x in bucket)/len(bucket), 4) if bucket else 0.0))
        self._calibration = tuple(fitted); return self
    @property
    def bins_report(self): return self._calibration
    def transform(self, confidence: float) -> float:
        value = max(0.0, min(1.0, confidence))
        for item in self._calibration:
            if item.count and item.lower <= value < item.upper: return item.accuracy
        populated = [item for item in self._calibration if item.count]
        return populated[-1].accuracy if populated else value
    def report(self): return [asdict(item) for item in self._calibration]
