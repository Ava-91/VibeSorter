from PIL import Image

from vibesorter.features import extract_features
from vibesorter.vibes import VibeScore, select_vibes


def test_spatial_features_are_exposed(tmp_path):
    path = tmp_path / "split.png"
    image = Image.new("RGB", (64, 64), "black")
    for x in range(32, 64):
        for y in range(32, 64):
            image.putpixel((x, y), (255, 240, 220))
    image.save(path)
    features = extract_features(path)
    assert len(features.regions) == 4
    assert features.center_brightness_delta > 0


def test_multi_vibe_selection_keeps_close_scores():
    scores = (VibeScore("Dark / Moody", 0.82), VibeScore("Retro Blue", 0.77), VibeScore("Bright / Colorful", 0.20))
    selected = select_vibes(scores)
    assert [item.name for item in selected] == ["Dark / Moody", "Retro Blue"]


def test_multi_vibe_selection_falls_back_to_winner():
    scores = (VibeScore("Dark / Moody", 0.80), VibeScore("Retro Blue", 0.31))
    assert select_vibes(scores) == (scores[0],)
