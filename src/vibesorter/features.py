from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

from PIL import Image, ImageOps, UnidentifiedImageError

ANALYSIS_SIZE = (64, 64)
PALETTE_SIZE = 6


@dataclass(frozen=True, slots=True)
class ColorSample:
    rgb: tuple[int, int, int]
    proportion: float


@dataclass(frozen=True, slots=True)
class SpatialRegion:
    brightness: float
    saturation: float
    warm_ratio: float
    cool_ratio: float


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
    text_likelihood: float
    colors: tuple[ColorSample, ...]
    regions: tuple[SpatialRegion, ...] = ()
    center_brightness_delta: float = 0.0
    center_saturation_delta: float = 0.0


def _text_likelihood(image: Image.Image, grayscale_ratio: float, contrast: float) -> float:
    gray = image.convert("L")
    width, height = gray.size
    pixels = list(gray.getdata())
    if width < 2 or height < 2:
        return 0.0
    edge_count = strong_edges = total_edges = 0
    for y in range(height - 1):
        row = y * width
        next_row = (y + 1) * width
        for x in range(width - 1):
            current = pixels[row + x]
            edge = max(abs(current - pixels[row + x + 1]), abs(current - pixels[next_row + x]))
            total_edges += 1
            edge_count += edge > 28
            strong_edges += edge > 64
    edge_density = edge_count / total_edges
    strong_edge_density = strong_edges / total_edges
    return max(0.0, min(1.0,
        0.45 * min(1.0, edge_density / 0.42)
        + 0.20 * min(1.0, strong_edge_density / 0.18)
        + 0.25 * grayscale_ratio
        + 0.10 * min(1.0, contrast / 0.45)
    ))


def _region_features(image: Image.Image) -> tuple[SpatialRegion, ...]:
    width, height = image.size
    regions: list[SpatialRegion] = []
    for row in range(2):
        for column in range(2):
            left, top = column * width // 2, row * height // 2
            right, bottom = (column + 1) * width // 2, (row + 1) * height // 2
            pixels = list(image.crop((left, top, right, bottom)).convert("HSV").getdata())
            if not pixels:
                regions.append(SpatialRegion(0.0, 0.0, 0.0, 0.0))
                continue
            brightness = sum(v for _, _, v in pixels) / len(pixels) / 255.0
            saturation = sum(s for _, s, _ in pixels) / len(pixels) / 255.0
            warm = cool = 0
            for hue, sat, _ in pixels:
                if sat < 0.18:
                    continue
                normalized = hue / 255.0
                if normalized < 0.16 or normalized >= 0.92:
                    warm += 1
                elif 0.48 <= normalized <= 0.72:
                    cool += 1
            regions.append(SpatialRegion(brightness, saturation, warm / len(pixels), cool / len(pixels)))
    return tuple(regions)


def extract_features(path: str | Path) -> ImageFeatures:
    """Extract lightweight global and spatial visual signals."""
    image_path = Path(path).expanduser()
    try:
        with Image.open(image_path) as source:
            source.verify()
        with Image.open(image_path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail(ANALYSIS_SIZE, Image.Resampling.LANCZOS)
            hsv_image = image.convert("HSV")
            rgb_pixels = image.getdata()
            hsv_pixels = hsv_image.getdata()

            counts: dict[tuple[int, int, int], int] = {}
            sum_r = sum_g = sum_b = 0
            sum_h = sum_s = sum_v = 0
            sum_luminance = sum_luminance_sq = 0.0
            warm = cool = grayscale = dark = light = count = 0

            for (r, g, b), (hue_byte, sat_byte, value_byte) in zip(rgb_pixels, hsv_pixels):
                count += 1
                sum_r += r; sum_g += g; sum_b += b
                sum_h += hue_byte; sum_s += sat_byte; sum_v += value_byte
                luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
                sum_luminance += luminance; sum_luminance_sq += luminance * luminance
                key = ((r // 16) * 16 + 8, (g // 16) * 16 + 8, (b // 16) * 16 + 8)
                counts[key] = counts.get(key, 0) + 1
                sat = sat_byte / 255.0; value = value_byte / 255.0; hue = hue_byte / 255.0
                grayscale += sat < 0.18
                dark += value < 0.25
                light += value > 0.78
                if sat >= 0.18:
                    if hue < 0.16 or hue >= 0.92:
                        warm += 1
                    elif 0.48 <= hue <= 0.72:
                        cool += 1
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupted image: {image_path}") from exc
    except OSError as exc:
        raise ValueError(f"Could not read image: {image_path} ({exc})") from exc

    if not count:
        raise ValueError(f"Image contains no pixels: {image_path}")

    mean_luminance = sum_luminance / count
    variance = max(0.0, (sum_luminance_sq / count) - mean_luminance * mean_luminance)
    contrast = min(1.0, math.sqrt(variance) / 255.0)
    grayscale_ratio = grayscale / count
    top = sorted(counts.items(), key=lambda item: item[1], reverse=True)[:PALETTE_SIZE]
    colors = tuple(ColorSample(rgb=color, proportion=amount / count) for color, amount in top)
    regions = _region_features(image)
    center = regions[3] if regions else SpatialRegion(0.0, 0.0, 0.0, 0.0)
    edge_regions = regions[:3]
    edge_brightness = sum(item.brightness for item in edge_regions) / len(edge_regions) if edge_regions else center.brightness
    edge_saturation = sum(item.saturation for item in edge_regions) / len(edge_regions) if edge_regions else center.saturation

    return ImageFeatures(
        path=image_path,
        average_rgb=(round(sum_r / count), round(sum_g / count), round(sum_b / count)),
        average_hsv=(sum_h / count / 255.0, sum_s / count / 255.0, sum_v / count / 255.0),
        brightness=sum_v / count / 255.0,
        saturation=sum_s / count / 255.0,
        contrast=contrast,
        warm_ratio=warm / count,
        cool_ratio=cool / count,
        grayscale_ratio=grayscale_ratio,
        dark_ratio=dark / count,
        light_ratio=light / count,
        text_likelihood=_text_likelihood(image, grayscale_ratio, contrast),
        colors=colors,
        regions=regions,
        center_brightness_delta=round(center.brightness - edge_brightness, 4),
        center_saturation_delta=round(center.saturation - edge_saturation, 4),
    )
