from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from vibesorter.features import extract_features


def test_text_like_image_gets_a_nonzero_text_signal(tmp_path: Path) -> None:
    image = Image.new("RGB", (160, 100), "white")
    draw = ImageDraw.Draw(image)
    for y in range(12, 90, 12):
        draw.rectangle((12, y, 145, y + 4), fill="black")
    path = tmp_path / "text-card.png"
    image.save(path)

    features = extract_features(path)

    assert features.text_likelihood > 0.35


def test_flat_photo_like_color_does_not_look_text_heavy(tmp_path: Path) -> None:
    path = tmp_path / "flat.png"
    Image.new("RGB", (160, 100), (40, 100, 210)).save(path)

    features = extract_features(path)

    assert features.text_likelihood < 0.35
