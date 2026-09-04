from vibesorter.taxonomy import (
    ATTRIBUTE_CARDINALITY,
    ATTRIBUTE_FAMILIES,
    TAXONOMY_VERSION,
    Brightness,
    Color,
    MediaType,
    Saturation,
    Temperature,
    Vibe,
    is_valid_attribute_value,
)


def test_taxonomy_has_independent_attribute_families():
    assert ATTRIBUTE_FAMILIES == (
        "media_type",
        "colors",
        "temperature",
        "saturation",
        "brightness",
        "vibes",
    )


def test_multi_valued_families_are_explicit():
    assert ATTRIBUTE_CARDINALITY["colors"] == "multi"
    assert ATTRIBUTE_CARDINALITY["vibes"] == "multi"
    assert ATTRIBUTE_CARDINALITY["media_type"] == "single"
    assert ATTRIBUTE_CARDINALITY["temperature"] == "single"


def test_taxonomy_values_are_machine_friendly():
    assert MediaType.PHOTOGRAPH.value == "photograph"
    assert Color.RED.value == "red"
    assert Temperature.COOL.value == "cool"
    assert Saturation.MUTED.value == "muted"
    assert Brightness.DARK.value == "dark"
    assert Vibe.RETRO.value == "retro"


def test_compound_labels_are_not_canonical_values():
    assert not is_valid_attribute_value("vibes", "Retro Blue")
    assert not is_valid_attribute_value("vibes", "Dark / Moody")
    assert is_valid_attribute_value("vibes", "retro")
    assert TAXONOMY_VERSION == "2.0"
