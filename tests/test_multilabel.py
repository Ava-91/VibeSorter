from vibesorter.annotation import ImageAnnotation
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.learned_profile import LearnedProfileClassifier
from vibesorter.multilabel import evaluate_family
from vibesorter.profile import AttributeValue, ImageProfile


def profile(colors=(), vibes=()):
    return ImageProfile(
        media_type=AttributeValue("photograph", 1.0),
        colors=tuple(AttributeValue(value, 1.0) for value in colors),
        temperature=AttributeValue("cool", 1.0),
        saturation=AttributeValue("muted", 1.0),
        brightness=AttributeValue("dark", 1.0),
        vibes=tuple(AttributeValue(value, 1.0) for value in vibes),
    )


def test_multilabel_metrics_do_not_collapse_multiple_values():
    expected = (profile(("red", "blue"), ("retro", "moody")),)
    predicted = (profile(("red", "blue"), ("retro",)),)
    metrics = evaluate_family(expected, predicted, "vibes")
    assert metrics.exact_matches == 0
    assert metrics.micro_precision == 1.0
    assert metrics.micro_recall == 0.5
    assert metrics.micro_f1 == round(2 / 3, 4)


def test_learned_profile_model_trains_per_family(tmp_path):
    image = tmp_path / "a.jpg"
    image.write_bytes(b"x")
    annotation = ImageAnnotation(image, profile(("red",), ("retro",)))
    # Training is validated structurally here; feature extraction is mocked by
    # using a real lightweight feature object through the model's feature path.
    from vibesorter import learned_profile
    original = learned_profile.extract_features

    def fake_extract_features(_):
        return ImageFeatures(
            path=image, average_rgb=(120, 40, 40), average_hsv=(0.0, 0.6, 0.5),
            brightness=0.5, saturation=0.6, contrast=0.2, warm_ratio=0.4, cool_ratio=0.1,
            grayscale_ratio=0.1, dark_ratio=0.2, light_ratio=0.1, text_likelihood=0.1,
            colors=(ColorSample((120, 40, 40), 1.0),),
        )

    learned_profile.extract_features = fake_extract_features
    try:
        model = LearnedProfileClassifier.fit((annotation,))
        assert set(model.centroids) == {"media_type", "colors", "temperature", "saturation", "brightness", "vibes"}
        model.save(tmp_path / "model.json")
        assert LearnedProfileClassifier.load(tmp_path / "model.json") == model
    finally:
        learned_profile.extract_features = original
