from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .profile import ImageProfile
from .taxonomy import ATTRIBUTE_FAMILIES


@dataclass(frozen=True, slots=True)
class MultiLabelMetrics:
    family: str
    total: int
    exact_matches: int
    exact_match_rate: float
    micro_precision: float
    micro_recall: float
    micro_f1: float
    per_attribute: dict[str, dict[str, float | int]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "total": self.total,
            "exact_matches": self.exact_matches,
            "exact_match_rate": self.exact_match_rate,
            "micro_precision": self.micro_precision,
            "micro_recall": self.micro_recall,
            "micro_f1": self.micro_f1,
            "per_attribute": self.per_attribute,
        }


def _values(profile: ImageProfile, family: str) -> set[str]:
    value = getattr(profile, family)
    if family in {"colors", "vibes"}:
        return {item.value for item in value}
    return {value.value} if value is not None else set()


def evaluate_family(
    expected: tuple[ImageProfile, ...],
    predicted: tuple[ImageProfile, ...],
    family: str,
) -> MultiLabelMetrics:
    """Evaluate one family without collapsing multi-valued predictions."""
    if family not in ATTRIBUTE_FAMILIES:
        raise ValueError(f"unknown attribute family: {family}")
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted datasets must have equal length")
    if not expected:
        return MultiLabelMetrics(family, 0, 0, 0.0, 0.0, 0.0, 0.0)

    true_positive = false_positive = false_negative = exact = 0
    support: dict[str, int] = {}
    hits: dict[str, int] = {}
    predicted_counts: dict[str, int] = {}
    for actual, guess in zip(expected, predicted):
        actual_values, predicted_values = _values(actual, family), _values(guess, family)
        exact += actual_values == predicted_values
        true_positive += len(actual_values & predicted_values)
        false_positive += len(predicted_values - actual_values)
        false_negative += len(actual_values - predicted_values)
        for value in actual_values:
            support[value] = support.get(value, 0) + 1
            if value in predicted_values:
                hits[value] = hits.get(value, 0) + 1
        for value in predicted_values:
            predicted_counts[value] = predicted_counts.get(value, 0) + 1

    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    attributes = sorted(set(support) | set(predicted_counts))
    per_attribute = {}
    for value in attributes:
        tp = hits.get(value, 0)
        actual_count = support.get(value, 0)
        predicted_count = predicted_counts.get(value, 0)
        p = tp / predicted_count if predicted_count else 0.0
        r = tp / actual_count if actual_count else 0.0
        per_attribute[value] = {
            "support": actual_count,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0,
        }
    return MultiLabelMetrics(
        family, len(expected), exact, round(exact / len(expected), 4),
        round(precision, 4), round(recall, 4), round(f1, 4), per_attribute,
    )


def evaluate_profiles(
    expected: tuple[ImageProfile, ...],
    predictor: Callable[[int], ImageProfile],
) -> dict[str, MultiLabelMetrics]:
    """Evaluate every taxonomy family using an index-based predictor."""
    predicted = tuple(predictor(index) for index in range(len(expected)))
    return {family: evaluate_family(expected, predicted, family) for family in ATTRIBUTE_FAMILIES}
