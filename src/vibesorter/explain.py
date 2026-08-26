from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .diagnostics import diagnose
from .features import extract_features
from .vibes import score_vibes


@dataclass(frozen=True, slots=True)
class Explanation:
    path: Path
    winner: str
    confidence: float
    margin: float
    ambiguous: bool
    scores: tuple[tuple[str, float], ...]
    features: dict

    def to_dict(self) -> dict:
        data = asdict(self)
        data["path"] = str(self.path)
        return data


def explain_image(path: str | Path) -> Explanation:
    image = Path(path)
    features = extract_features(image)
    diagnostic = diagnose(features)
    return Explanation(
        image,
        diagnostic.winner.name,
        diagnostic.confidence,
        diagnostic.margin,
        diagnostic.ambiguous,
        tuple((score.name, score.score) for score in score_vibes(features)),
        asdict(features),
    )
