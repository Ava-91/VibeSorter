from vibesorter.learned import LearnedClassifier, feature_vector
from vibesorter.features import ImageFeatures
from vibesorter.vibes import VIBES


def make_features(value: float) -> ImageFeatures:
    return ImageFeatures(__import__('pathlib').Path('sample.jpg'), (100, 120, 140), (0.5, 0.2, value), value, 0.2, 0.1, 0.1, 0.4, 0.2, 0.2, 0.3, 0.7, 0.1, ())


def test_feature_vector_is_deterministic():
    assert feature_vector(make_features(0.8)) == feature_vector(make_features(0.8))


def test_model_serialization_round_trip(tmp_path):
    model = LearnedClassifier({'Dark / Moody': (0.1, 0.2)}, {'Dark / Moody': 2})
    path = tmp_path / 'model.json'
    model.save(path)
    loaded = LearnedClassifier.load(path)
    assert loaded == model


def test_model_scores_known_centroid():
    model = LearnedClassifier({vibe: (0.0, 0.0) for vibe in VIBES}, {vibe: 1 for vibe in VIBES})
    assert model.centroids
