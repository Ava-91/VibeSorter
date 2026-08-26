from vibesorter.features import extract_features


def test_extracted_features_stay_normalized(image_factory):
    path = image_factory("warm.png", (220, 90, 40))
    features = extract_features(path)
    for value in (
        features.brightness, features.saturation, features.contrast,
        features.grayscale_ratio, features.dark_ratio, features.light_ratio,
        features.warm_ratio, features.cool_ratio,
    ):
        assert 0 <= value <= 1
