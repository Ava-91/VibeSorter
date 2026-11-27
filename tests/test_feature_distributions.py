from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from vibesorter.features import FEATURE_VERSION, extract_features


def _save(image: Image.Image, path: Path):
    image.save(path)
    return extract_features(path)


def test_uniform_image_has_stable_distribution_and_no_edges(tmp_path: Path):
    features = _save(Image.new("RGB", (96, 64), (90, 120, 150)), tmp_path / "uniform.png")
    assert len(features.luminance_percentiles) == 5
    assert len(features.saturation_percentiles) == 5
    assert len(set(features.luminance_percentiles)) == 1
    assert features.edge_density == 0.0
    assert features.color_diversity == 1 / 32
    assert features.alpha_coverage == 1.0


def test_gradient_has_ordered_luminance_percentiles(tmp_path: Path):
    image = Image.new("RGB", (128, 64))
    for x in range(image.width):
        value = round(x / (image.width - 1) * 255)
        for y in range(image.height):
            image.putpixel((x, y), (value, value, value))
    features = _save(image, tmp_path / "gradient.png")
    values = features.luminance_percentiles
    assert values == tuple(sorted(values))
    assert values[0] < values[2] < values[-1]
    assert features.edge_density > 0


def test_mixed_regions_preserve_small_vivid_accent_color(tmp_path: Path):
    image = Image.new("RGB", (128, 128), (128, 128, 128))
    ImageDraw.Draw(image).rectangle((0, 0, 35, 35), fill=(255, 0, 180))
    features = _save(image, tmp_path / "accent.png")
    assert any(color.rgb[0] > 200 and color.rgb[2] > 120 for color in features.colors)
    assert len(features.regions) == 4


def test_high_contrast_image_has_more_edges_and_color_diversity(tmp_path: Path):
    image = Image.new("RGB", (128, 128), "black")
    draw = ImageDraw.Draw(image)
    for x in range(0, 128, 8):
        draw.rectangle((x, 0, x + 3, 127), fill="white" if (x // 8) % 2 else "red")
    features = _save(image, tmp_path / "stripes.png")
    assert features.edge_density > 0.05
    assert features.color_diversity > 0


def test_transparent_pixels_are_composited_and_alpha_is_recorded(tmp_path: Path):
    image = Image.new("RGBA", (64, 64), (255, 0, 255, 0))
    ImageDraw.Draw(image).rectangle((0, 0, 31, 63), fill=(0, 0, 255, 255))
    features = _save(image, tmp_path / "transparent.png")
    assert 0.45 <= features.alpha_coverage <= 0.55
    assert features.average_rgb[2] > features.average_rgb[0]
    assert FEATURE_VERSION == 3
