from __future__ import annotations

from PIL import Image

from vibesorter.features import extract_features

# Regression fixture: Pillow-supported extensions that are cheap to create in-memory.
TEST_FORMATS = ("PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP")


def test_supported_formats_are_discovered(tmp_path):
    from vibesorter.scanner import IMAGE_EXTENSIONS, find_images

    for index, fmt in enumerate(TEST_FORMATS):
        image = Image.new("RGB", (8, 8), (20 + index * 20, 80, 140))
        path = tmp_path / f"sample_{index}.{fmt.lower()}"
        image.save(path, format=fmt)

    found = find_images(tmp_path)
    assert len(found) == len(TEST_FORMATS)
    assert all(path.suffix.lower() in IMAGE_EXTENSIONS for path in found)


def test_exif_orientation_is_applied_without_modifying_file(tmp_path):
    path = tmp_path / "oriented.jpg"
    image = Image.new("RGB", (20, 10), "red")
    exif = image.getexif()
    exif[274] = 6  # Rotate 90° clockwise on display.
    image.save(path, exif=exif)
    before = path.read_bytes()

    features = extract_features(path)

    assert features.path == path
    assert path.read_bytes() == before


def test_corrupt_image_gets_clear_error(tmp_path):
    path = tmp_path / "broken.jpg"
    path.write_bytes(b"not actually an image")

    try:
        extract_features(path)
    except ValueError as exc:
        assert "Unsupported or corrupted image" in str(exc)
    else:
        raise AssertionError("corrupt image should raise ValueError")
