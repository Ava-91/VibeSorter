from vibesorter.explain import explain_image


def test_explanation_contains_scores_and_features(image_factory):
    path = image_factory("sample.png", (40, 100, 210))
    explanation = explain_image(path)
    assert explanation.winner
    assert explanation.scores
    assert explanation.features
    assert 0 <= explanation.confidence <= 1


def test_explanation_is_serializable(image_factory):
    path = image_factory("sample.png")
    assert explain_image(path).to_dict()["path"] == str(path)
