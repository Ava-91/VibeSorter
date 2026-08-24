from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from PIL import Image


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


def extract_features(path: str | Path) -> ImageFeatures:
    """Extract lightweight visual signals from an image without any cloud API."""
    image_path = Path(path).expanduser()
    with Image.open(image_path) as source:
        image = source.convert("RGB")
        image.thumbnail(ANALYSIS_SIZE, Image.Resampling.LANCZOS)
        hsv_image = image.convert("HSV")
        rgb_pixels = image.getdata()
        hsv_pixels = hsv_image.getdata()

        counts: dict[tuple[int, int, int], int] = {}
        sum_r = sum_g = sum_b = 0
        sum_h = sum_s = sum_v = 0
        sum_luminance = sum_luminance_sq = 0.0
        warm = cool = grayscale = dark = light = 0
        count = 0

        # Keep all feature extraction in one native-backed pixel pass. The old
        # implementation repeatedly walked the same pixels for averages, HSV,
        # luminance/contrast, vibe ratios, and the representative palette.
        for (r, g, b), (hue_byte, sat_byte, value_byte) in zip(rgb_pixels, hsv_pixels):
            count += 1
            sum_r += r
            sum_g += g
            sum_b += b
            sum_h += hue_byte
            sum_s += sat_byte
            sum_v += value_byte

            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            sum_luminance += luminance
            sum_luminance_sq += luminance * luminance

            key = ((r // 16) * 16 + 8, (g // 16) * 16 + 8, (b // 16) * 16 + 8)
            counts[key] = counts.get(key, 0) + 1

            sat = sat_byte / 255.0
            value = value_byte / 255.0
            hue = hue_byte / 255.0
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

    if not count:
        raise ValueError(f"Image contains no pixels: {image_path}")

    mean_luminance = sum_luminance / count
    variance = max(0.0, (sum_luminance_sq / count) - (mean_luminance * mean_luminance))
    contrast = math.sqrt(variance) / 255.0

    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:PALETTE_SIZE]
    colors = tuple(
        ColorSample(rgb=color, proportion=amount / count)
        for color, amount in top
    )

    return ImageFeatures(
        path=image_path,
        average_rgb=(
            round(sum_r / count),
            round(sum_g / count),
            round(sum_b / count),
        ),
        average_hsv=(
            sum_h / count / 255.0,
            sum_s / count / 255.0,
            sum_v / count / 255.0,
        ),
        brightness=sum_v / count / 255.0,
        saturation=sum_s / count / 255.0,
        contrast=min(1.0, contrast),
        warm_ratio=warm / count,
        cool_ratio=cool / count,
        grayscale_ratio=grayscale / count,
        dark_ratio=dark / count,
        light_ratio=light / count,
        colors=colors,
    )
