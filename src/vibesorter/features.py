from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import math

from PIL import Image, ImageStat


# 64x64 keeps enough detail for vibe classification while cutting per-image
# pixel work by more than half compared with the previous 96x96 analysis size.
ANALYSIS_SIZE = (64, 64)
PALETTE_SIZE = 6


@dataclass(frozen=True, slots=True)
class ColorSample:
    rgb: tuple[int, int, int]
    proportion: float


@dataclass(frozen=True, slots=True)
class ImageFeatures:
    path: Path
    average_rgb: tuple[int, int, int]
    average_hsv: tuple[float, float, float]
    brightness: float
    saturation: float
    contrast: float
    warm_ratio: float
    cool_ratio: float
    grayscale_ratio: float
    dark_ratio: float
    light_ratio: float
    colors: tuple[ColorSample, ...]


def _iter_pixels(image: Image.Image) -> Iterable[tuple[int, int, int]]:
    return image.getdata()


def _representative_colors(image: Image.Image, limit: int = PALETTE_SIZE) -> tuple[ColorSample, ...]:
    # Quantize to 4 bits/channel. This gives a stable, cheap 4096-bin palette.
    counts: dict[tuple[int, int, int], int] = {}
    total = 0
    for r, g, b in _iter_pixels(image):
        key = ((r // 16) * 16 + 8, (g // 16) * 16 + 8, (b // 16) * 16 + 8)
        counts[key] = counts.get(key, 0) + 1
        total += 1

    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:limit]
    return tuple(
        ColorSample(rgb=color, proportion=count / total)
        for color, count in top
    )


def extract_features(path: str | Path) -> ImageFeatures:
    """Extract lightweight visual signals from an image without any cloud API."""
    image_path = Path(path).expanduser()
    with Image.open(image_path) as source:
        image = source.convert("RGB")
        image.thumbnail(ANALYSIS_SIZE, Image.Resampling.LANCZOS)
        pixels = list(_iter_pixels(image))
        # Let Pillow's native implementation handle RGB -> HSV instead of
        # calling colorsys.rgb_to_hsv once per pixel in Python.
        hsv_values = list(image.convert("HSV").getdata())

    if not pixels:
        raise ValueError(f"Image contains no pixels: {image_path}")

    count = len(pixels)
    avg = tuple(round(sum(pixel[channel] for pixel in pixels) / count) for channel in range(3))
    avg_hsv = tuple(
        sum(value[channel] / 255.0 for value in hsv_values) / count
        for channel in range(3)
    )

    brightness = avg_hsv[2]
    saturation = avg_hsv[1]
    luminances = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels]
    mean_luminance = sum(luminances) / count
    contrast = math.sqrt(sum((value - mean_luminance) ** 2 for value in luminances)) / 255.0

    warm = cool = grayscale = dark = light = 0
    for hue_byte, sat_byte, value_byte in hsv_values:
        hue = hue_byte / 255.0
        sat = sat_byte / 255.0
        value = value_byte / 255.0
        if sat < 0.18:
            grayscale += 1
        if value < 0.25:
            dark += 1
        if value > 0.78:
            light += 1
        # Red/orange/yellow are warm; cyan/blue are cool. Green stays neutral.
        if sat >= 0.18:
            if hue < 0.16 or hue >= 0.92:
                warm += 1
            elif 0.48 <= hue <= 0.72:
                cool += 1

    return ImageFeatures(
        path=image_path,
        average_rgb=avg,
        average_hsv=avg_hsv,
        brightness=brightness,
        saturation=saturation,
        contrast=min(1.0, contrast),
        warm_ratio=warm / count,
        cool_ratio=cool / count,
        grayscale_ratio=grayscale / count,
        dark_ratio=dark / count,
        light_ratio=light / count,
        colors=_representative_colors(image),
    )
