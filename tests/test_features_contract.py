from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import vibesorter.features as features_module
from vibesorter.features import extract_features


def test_corrupt_image_fails_with_a_predictable_error(tmp_path: Path) -> None:
    image = tmp_path / "broken.jpg"
    image.write_bytes(b"not an image")

    with pytest.raises(ValueError, match="Unsupported or corrupted image"):
        extract_features(image)


def test_oversized_image_is_rejected_before_pixel_processing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image = tmp_path / "large.png"
    Image.new("RGB", (11, 10), "red").save(image)
    monkeypatch.setattr(features_module, "MAX_IMAGE_PIXELS", 100)

    with pytest.raises(ValueError, match="100-pixel safety limit"):
        extract_features(image)


def test_exif_orientation_is_applied_before_feature_extraction(tmp_path: Path) -> None:
    original = Image.new("RGB", (32, 16), "black")
    for x in range(32):
        for y in range(16):
            original.putpixel((x, y), "red" if x < 16 else "blue")

    exif = Image.Exif()
    exif[274] = 6
    exif_path = tmp_path / "with-orientation.png"
    oriented_path = tmp_path / "already-oriented.png"
    original.save(exif_path, exif=exif)
    original.transpose(Image.Transpose.ROTATE_270).save(oriented_path)

    actual = extract_features(exif_path)
    expected = extract_features(oriented_path)
    assert actual.average_rgb == expected.average_rgb
    assert actual.regions == expected.regions
    assert actual.center_brightness_delta == expected.center_brightness_delta


def test_multiframe_image_uses_first_frame_deterministically(tmp_path: Path) -> None:
    image = tmp_path / "animated.gif"
    first = Image.new("RGB", (16, 16), "red")
    second = Image.new("RGB", (16, 16), "blue")
    first.save(image, save_all=True, append_images=[second], duration=100, loop=0)

    features = extract_features(image)

    assert features.average_rgb[0] > 200
    assert features.average_rgb[2] < 50
