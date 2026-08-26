from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .features import ColorSample, ImageFeatures
from .vibes import VibeScore

CACHE_VERSION = 1
DEFAULT_CACHE_PATH = Path(".vibesorter") / "analysis.json"


def _feature_to_dict(features: ImageFeatures) -> dict:
    data = asdict(features)
    data["path"] = str(features.path)
    return data


def _feature_from_dict(data: dict) -> ImageFeatures:
    return ImageFeatures(
        path=Path(data["path"]),
        average_rgb=tuple(data["average_rgb"]),
        average_hsv=tuple(data["average_hsv"]),
        brightness=float(data["brightness"]),
        saturation=float(data["saturation"]),
        contrast=float(data["contrast"]),
        warm_ratio=float(data["warm_ratio"]),
        cool_ratio=float(data["cool_ratio"]),
        grayscale_ratio=float(data["grayscale_ratio"]),
        dark_ratio=float(data["dark_ratio"]),
        light_ratio=float(data["light_ratio"]),
        text_likelihood=float(data["text_likelihood"]),
        colors=tuple(
            ColorSample(tuple(item["rgb"]), float(item["proportion"]))
            for item in data.get("colors", [])
        ),
    )


def _result_to_dict(features: ImageFeatures, scores: tuple[VibeScore, ...]) -> dict:
    return {
        "features": _feature_to_dict(features),
        "scores": [{"name": score.name, "score": score.score} for score in scores],
    }


def _result_from_dict(data: dict) -> tuple[ImageFeatures, tuple[VibeScore, ...]]:
    features = _feature_from_dict(data["features"])
    scores = tuple(VibeScore(item["name"], float(item["score"])) for item in data["scores"])
    return features, scores


class AnalysisCache:
    """Small versioned JSON cache for local image analysis results."""

    def __init__(self, path: str | Path = DEFAULT_CACHE_PATH) -> None:
        self.path = Path(path).expanduser()
        self._entries: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            self._entries = {}
            return
        if data.get("version") != CACHE_VERSION or not isinstance(data.get("entries"), dict):
            self._entries = {}
            return
        self._entries = data["entries"]

    def get(self, path: str | Path) -> tuple[ImageFeatures, tuple[VibeScore, ...]] | None:
        entry = self._entries.get(str(Path(path).expanduser()))
        if entry is None:
            return None
        try:
            return _result_from_dict(entry["result"])
        except (KeyError, TypeError, ValueError):
            return None

    def set(self, path: str | Path, features: ImageFeatures, scores: tuple[VibeScore, ...]) -> None:
        key = str(Path(path).expanduser())
        self._entries[key] = {"result": _result_to_dict(features, scores)}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": CACHE_VERSION, "entries": self._entries}
        fd, temporary = tempfile.mkstemp(prefix="analysis-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
