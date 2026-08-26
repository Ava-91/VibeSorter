from vibesorter.features import extract_features
from vibesorter.vibes import confidence_score, is_confident, score_vibes


def test_scores_are_sorted_and_bounded(image_factory):
    path = image_factory("blue.png", (40, 90, 220))
    scores = score_vibes(extract_features(path))
    assert scores
    assert list(scores) == sorted(scores, key=lambda item: item.score, reverse=True)
    assert all(0 <= item.score <= 1 for item in scores)


def test_confidence_is_bounded(image_factory):
    path = image_factory("gray.png", (128, 128, 128))
    scores = score_vibes(extract_features(path))
    assert 0 <= confidence_score(scores) <= 1
    assert isinstance(is_confident(scores), bool)
