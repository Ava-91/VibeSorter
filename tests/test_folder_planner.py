from pathlib import Path

from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.folder_planner import build_attribute_proposal
from vibesorter.pipeline import AnalysisResult
from vibesorter.profile import AttributeValue, ImageProfile
from vibesorter.vibes import VibeScore


def result(path: Path) -> AnalysisResult:
    features = ImageFeatures(
        path,
        (20, 40, 80),
        (0.6, 0.5, 0.5),
        0.5,
        0.5,
        0.3,
        0.1,
        0.7,
        0.05,
        0.2,
        0.3,
        0.1,
        (ColorSample((20, 40, 80), 1.0),),
    )
    scores = (VibeScore("retro", 0.8),)
    return AnalysisResult(path, features, scores[0], scores, cached=True)


def profile(media: str, colors: tuple[str, ...], vibes: tuple[str, ...]) -> ImageProfile:
    return ImageProfile(
        media_type=AttributeValue(media, 0.95),
        colors=tuple(AttributeValue(value, 0.8) for value in colors),
        temperature=AttributeValue("cool", 0.9),
        saturation=AttributeValue("muted", 0.8),
        brightness=AttributeValue("dark", 0.8),
        vibes=tuple(AttributeValue(value, 0.7) for value in vibes),
    )


def test_planner_uses_one_primary_folder_and_keeps_multilabel_metadata(
    tmp_path: Path,
) -> None:
    image = tmp_path / "a.jpg"
    image.write_bytes(b"a")
    proposal = build_attribute_proposal(
        [result(image)],
        {image: profile("photograph", ("red", "blue"), ("retro", "moody"))},
        tmp_path / "Sorted",
    )
    assert proposal.version == 2
    destination = Path(proposal.operations[0].destination)
    assert destination.relative_to(tmp_path / "Sorted") == Path("photograph/a.jpg")


def test_planner_can_choose_color_as_primary_attribute(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"
    image.write_bytes(b"a")
    proposal = build_attribute_proposal(
        [result(image)],
        {image: profile("photograph", ("red", "blue"), ("retro",))},
        tmp_path / "Sorted",
        primary_attribute="colors",
    )
    destination = Path(proposal.operations[0].destination)
    assert destination.relative_to(tmp_path / "Sorted") == Path("red/a.jpg")


def test_planner_resolves_filename_collisions_deterministically(tmp_path: Path) -> None:
    first = tmp_path / "one" / "a.jpg"
    second = tmp_path / "two" / "a.jpg"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    results = [result(first), result(second)]
    profiles = {
        first: profile("photograph", ("red",), ("retro",)),
        second: profile("photograph", ("red",), ("moody",)),
    }
    proposal = build_attribute_proposal(results, profiles, tmp_path / "Sorted")
    destinations = [Path(item.destination) for item in proposal.operations]
    root = tmp_path / "Sorted"
    assert destinations[0].relative_to(root) == Path("photograph/a.jpg")
    assert destinations[1].relative_to(root) == Path("photograph/a (2).jpg")


def test_planner_rejects_unknown_attribute(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"
    image.write_bytes(b"a")
    try:
        build_attribute_proposal(
            [result(image)], {}, tmp_path / "Sorted", primary_attribute="unknown"
        )
    except ValueError as exc:
        assert "unknown folder attribute" in str(exc)
    else:
        raise AssertionError("unknown attribute should fail")
