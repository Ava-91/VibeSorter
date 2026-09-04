from __future__ import annotations

from .annotation import ImageAnnotation, load_annotations, save_annotation
from .cache import AnalysisCache
from .classifier import classify_profile
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
from .learned_profile import LearnedProfileClassifier
from .library import LibraryAnalysisStats, analyze_library, analyze_library_stats
from .multilabel import MultiLabelMetrics, evaluate_family, evaluate_profiles
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
from .vibes import VibeScore, classify, score_vibes, select_vibes

__all__ = [
    "ATTRIBUTE_CARDINALITY",
    "ATTRIBUTE_FAMILIES",
    "TAXONOMY_VERSION",
    "AnalysisCache",
    "AnalysisResult",
    "AttributeValue",
    "Brightness",
    "ClassificationMetrics",
    "Color",
    "ColorSample",
    "ConfidenceCalibrator",
    "ConfidenceObservation",
    "ImageAnnotation",
    "ImageFeatures",
    "ImageProfile",
    "ImageQuery",
    "LabelledImage",
    "LearnedClassifier",
    "LearnedProfileClassifier",
    "LibraryAnalysisStats",
    "MediaType",
    "MultiLabelMetrics",
    "Saturation",
    "SpatialRegion",
    "Temperature",
    "Vibe",
    "VibeScore",
    "analyze_folder",
    "analyze_image",
    "analyze_library",
    "analyze_library_stats",
    "classify",
    "classify_profile",
    "collect_confidence_observations",
    "evaluate_classifier",
    "evaluate_family",
    "evaluate_labels",
    "evaluate_profiles",
    "extract_features",
    "feature_vector",
    "load_annotations",
    "load_labels",
    "save_annotation",
    "score_vibes",
    "search_cache",
    "select_vibes",
]
