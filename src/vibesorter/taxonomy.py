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

ATTRIBUTE_CARDINALITY = {
    "media_type": "single",
    "colors": "multi",
    "temperature": "single",
    "saturation": "single",
    "brightness": "single",
    "vibes": "multi",
}

TAXONOMY_VERSION = "2.0"

ATTRIBUTE_ENUMS = {
    "media_type": MediaType,
    "colors": Color,
    "temperature": Temperature,
    "saturation": Saturation,
    "brightness": Brightness,
    "vibes": Vibe,
}


def is_valid_attribute_value(family: str, value: str) -> bool:
    """Return whether a value belongs to the canonical family vocabulary."""
    enum_type = ATTRIBUTE_ENUMS.get(family)
    return enum_type is not None and value in {item.value for item in enum_type}
