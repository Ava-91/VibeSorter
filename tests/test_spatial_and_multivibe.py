from PIL import Image

from vibesorter.features import extract_features
from vibesorter.vibes import VibeScore, select_vibes


def _features_for_image(tmp_path, name, painter):
    path = tmp_path / name
    image = Image.new("RGB", (64, 64), "black")
    painter(image)
    image.save(path)
    return extract_features(path)


def test_spatial_features_detect_a_bright_center(tmp_path):
    features = _features_for_image(
        tmp_path,
        "center.png",
        lambda image: [
            image.putpixel((x, y), (255, 240, 220))
            for x in range(16, 48)
            for y in range(16, 48)
        ],
    )
    assert len(features.regions) == 4
    assert features.center_brightness_delta > 0.5
    assert features.center_saturation_delta > 0


def test_spatial_features_do_not_mistake_bright_corner_for_center(tmp_path):
    features = _features_for_image(
        tmp_path,
        "corner.png",
        lambda image: [
            image.putpixel((x, y), (255, 240, 220))
            for x in range(48, 64)
            for y in range(48, 64)
        ],
    )
    assert features.center_brightness_delta < 0


def test_spatial_features_detect_bright_edges_outside_center(tmp_path):
    def paint_edges(image):
        for x in range(64):
            for y in range(64):
                if x < 8 or x >= 56 or y < 8 or y >= 56:
                    image.putpixel((x, y), (255, 240, 220))

    features = _features_for_image(tmp_path, "edges.png", paint_edges)
    assert features.center_brightness_delta < 0


def test_multi_vibe_selection_keeps_close_scores():
    scores = (VibeScore("Dark / Moody", 0.82), VibeScore("Retro Blue", 0.77), VibeScore("Bright / Colorful", 0.20))
    selected = select_vibes(scores)
    assert [item.name for item in selected] == ["Dark / Moody", "Retro Blue"]


def test_multi_vibe_selection_falls_back_to_winner():
    scores = (VibeScore("Dark / Moody", 0.80), VibeScore("Retro Blue", 0.31))
    assert select_vibes(scores) == (scores[0],)
