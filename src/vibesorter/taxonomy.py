from __future__ import annotations

from enum import StrEnum


class MediaType(StrEnum):
    PHOTOGRAPH = "photograph"
    ILLUSTRATION = "illustration"
    SCREENSHOT = "screenshot"
    GRAPHIC = "graphic"
    COLLAGE = "collage"


class Color(StrEnum):
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    PINK = "pink"
    NEUTRAL = "neutral"


class Temperature(StrEnum):
    WARM = "warm"
    COOL = "cool"
    NEUTRAL = "neutral"


class Saturation(StrEnum):
    VIBRANT = "vibrant"
    MUTED = "muted"
    DESATURATED = "desaturated"


class Brightness(StrEnum):
    BRIGHT = "bright"
    MID = "mid"
    DARK = "dark"


class Vibe(StrEnum):
    RETRO = "retro"
    DREAMY = "dreamy"
    SOFT = "soft"
    MOODY = "moody"
    MINIMAL = "minimal"
    COZY = "cozy"
    CINEMATIC = "cinematic"
    PLAYFUL = "playful"
    EDGY = "edgy"
    ROMANTIC = "romantic"


ATTRIBUTE_FAMILIES = (
    "media_type",
    "colors",
    "temperature",
    "saturation",
    "brightness",
    "vibes",
)

# Cardinality is part of the public taxonomy contract. A family marked multi
# may contain several values for the same image; this is intentional.
ATTRIBUTE_CARDINALITY = {
    "media_type": "single",
    "colors": "multi",
    "temperature": "single",
    "saturation": "single",
    "brightness": "single",
    "vibes": "multi",
}

LEGACY_COMPOUND_VIBES = (
    "Retro Blue",
    "Red / Warm",
    "Green & Black",
    "Black & White",
    "Soft / Pastel",
    "Dark / Moody",
    "Bright / Colorful",
    "Neutral / Photo Dump",
)

TAXONOMY_VERSION = "2.0"


def is_legacy_label(value: str) -> bool:
    """Return whether *value* belongs to the pre-v2 compound taxonomy."""
    return value in LEGACY_COMPOUND_VIBES
