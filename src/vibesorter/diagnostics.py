from __future__ import annotations

from dataclasses import asdict, dataclass

from .features import ImageFeatures
from .vibes import VibeScore, confidence_score, score_vibes


@dataclass(frozen=True, slots=True)
class ClassificationDiagnostic:
    winner: VibeScore
    runner_up: VibeScore | None
    margin: float
    confidence: float
    ambiguous: bool

    def to_dict(self) -> dict:
        data = asdict(self)
        data["winner"] = asdict(self.winner)
        data["runner_up"] = asdict(self.runner_up) if self.runner_up else None
        return data


def diagnose(features: ImageFeatures, *, ambiguity_margin: float = 0.08) -> ClassificationDiagnostic:
    if ambiguity_margin < 0:
        raise ValueError("ambiguity_margin must be non-negative")
    scores = score_vibes(features)
    winner = scores[0]
    runner_up = scores[1] if len(scores) > 1 else None
    margin = winner.score - (runner_up.score if runner_up else 0.0)
    return ClassificationDiagnostic(winner, runner_up, round(margin, 4), confidence_score(scores), margin < ambiguity_margin)
