from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .diagnostics import diagnose
from .features import extract_features
from .vibes import score_vibes, select_vibes

@dataclass(frozen=True, slots=True)
class Explanation:
    path: Path
    winner: str
    confidence: float
    margin: float
    ambiguous: bool
    selected_vibes: tuple[tuple[str, float], ...]
    scores: tuple[tuple[str, float], ...]
    feature_signals: dict[str, float]
    features: dict
    def to_dict(self) -> dict:
        data = asdict(self); data['path'] = str(self.path); return data

def explain_image(path: str | Path) -> Explanation:
    image = Path(path); features = extract_features(image); diagnostic = diagnose(features); scores = score_vibes(features); selected = select_vibes(scores)
    signals = {
        'brightness': round(features.brightness, 4), 'saturation': round(features.saturation, 4), 'contrast': round(features.contrast, 4),
        'warm_ratio': round(features.warm_ratio, 4), 'cool_ratio': round(features.cool_ratio, 4), 'dark_ratio': round(features.dark_ratio, 4),
        'light_ratio': round(features.light_ratio, 4), 'grayscale_ratio': round(features.grayscale_ratio, 4), 'text_likelihood': round(features.text_likelihood, 4),
        'center_brightness_delta': round(features.center_brightness_delta, 4), 'center_saturation_delta': round(features.center_saturation_delta, 4),
    }
    return Explanation(image, diagnostic.winner.name, diagnostic.confidence, diagnostic.margin, diagnostic.ambiguous, tuple((s.name, s.score) for s in selected), tuple((s.name, s.score) for s in scores), signals, asdict(features))
