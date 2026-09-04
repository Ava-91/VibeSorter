from pathlib import Path

from vibesorter.features import ImageFeatures
from vibesorter.learned import LearnedClassifier, feature_vector
from vibesorter.taxonomy import Vibe


def make_features(value: float) -> ImageFeatures:
    return ImageFeatures(
        Path("sample.jpg"),
        (100, 120, 140),
        (0.5, 0.2, value),
        value,
        0.2,
        0.1,
        0.1,
        0.4,
        0.2,
        0.2,
        0.3,
        0.7,
        (),
    )


def test_feature_vector_is_deterministic():
    assert feature_vector(make_features(0.8)) == feature_vector(make_features(0.8))


def test_model_serialization_round_trip(tmp_path):
    model = LearnedClassifier({"moody": (0.1, 0.2)}, {"moody": 2})
    path = tmp_path / "model.json"
    model.save(path)
    assert LearnedClassifier.load(path) == model


def test_model_scores_known_centroid():
    vibes = tuple(item.value for item in Vibe)
    model = LearnedClassifier({vibe: (0.0, 0.0) for vibe in vibes}, {vibe: 1 for vibe in vibes})
    assert model.centroids
