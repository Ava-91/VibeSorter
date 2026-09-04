from __future__ import annotations

from .cache import AnalysisCache
from .evaluation import (
    ClassificationMetrics,
    ConfidenceCalibrator,
    ConfidenceObservation,
    LabelledImage,
    collect_confidence_observations,
    evaluate_classifier,
    evaluate_labels,
    load_labels,
)
from .features import ColorSample, ImageFeatures, SpatialRegion, extract_features
from .learned import LearnedClassifier, feature_vector
from .library import LibraryAnalysisStats, analyze_library, analyze_library_stats
from .pipeline import AnalysisResult, analyze_folder, analyze_image
from .profile import AttributeValue, ImageProfile
from .search import ImageQuery, search_cache
from .taxonomy import (
    ATTRIBUTE_CARDINALITY,
    ATTRIBUTE_FAMILIES,
    TAXONOMY_VERSION,
    Brightness,
    Color,
    MediaType,
    Saturation,
    Temperature,
    Vibe,
)
from .vibes import VIBES, VibeScore, classify, score_vibes, select_vibes

__all__ = [
    "VIBES", "AnalysisCache", "AnalysisResult", "ATTRIBUTE_CARDINALITY",
    "ATTRIBUTE_FAMILIES", "AttributeValue", "Brightness", "ClassificationMetrics",
    "Color", "ColorSample", "ConfidenceCalibrator", "ConfidenceObservation",
    "ImageFeatures", "ImageProfile", "ImageQuery", "LabelledImage", "LearnedClassifier",
    "LibraryAnalysisStats", "MediaType", "Saturation", "SpatialRegion",
    "TAXONOMY_VERSION", "Temperature", "Vibe", "VibeScore", "analyze_folder",
    "analyze_image", "analyze_library", "analyze_library_stats", "classify",
    "collect_confidence_observations", "evaluate_classifier", "evaluate_labels",
    "extract_features", "feature_vector", "load_labels", "score_vibes",
    "search_cache", "select_vibes",
]
