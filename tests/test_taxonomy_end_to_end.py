from __future__ import annotations

from pathlib import Path

import pytest

from vibesorter.classifier import classify_profile
from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.folder_operations import apply_folder_plan, review_folder_plan, rollback_moves, validate_folder_plan
from vibesorter.folder_planner import build_attribute_proposal
from vibesorter.pipeline import AnalysisResult
from vibesorter.profile import AttributeValue, ImageProfile
from vibesorter.sqlite_cache import SQLiteAnalysisCache
from vibesorter.taxonomy import Vibe
from vibesorter.vibes import VibeScore


def make_features(path: Path) -> ImageFeatures:
    return ImageFeatures(
        path=path,
        average_rgb=(180, 40, 60),
        average_hsv=(0.98, 0.78, 0.70),
        brightness=0.70,
        saturation=0.78,
        contrast=0.30,
        warm_ratio=0.10,
        cool_ratio=0.45,
        grayscale_ratio=0.05,
        dark_ratio=0.10,
        light_ratio=0.30,
        text_likelihood=0.05,
        colors=(ColorSample((190, 40, 60), 0.65), ColorSample((40, 70, 180), 0.25)),
    )


def make_profile() -> ImageProfile:
    return ImageProfile(
        media_type=AttributeValue("photograph", 0.95),
        colors=(AttributeValue("red", 0.8), AttributeValue("blue", 0.7)),
        temperature=AttributeValue("cool", 0.9),
        saturation=AttributeValue("vibrant", 0.9),
        brightness=AttributeValue("bright", 0.88),
        vibes=(AttributeValue("retro", 0.8), AttributeValue("playful", 0.65)),
    )


def make_result(path: Path) -> AnalysisResult:
    features = make_features(path)
    score = VibeScore("retro", 0.8)
    return AnalysisResult(path, features, score, (score,), cached=True)


def test_profile_rejects_legacy_compound_values() -> None:
    with pytest.raises(ValueError, match="invalid vibes value"):
        ImageProfile(vibes=(AttributeValue("Retro Blue", 0.9),))


def test_classifier_emits_only_canonical_vibes() -> None:
    profile = classify_profile(make_features(Path("image.jpg")))
    canonical = {item.value for item in Vibe}
    assert {item.value for item in profile.vibes} <= canonical
    assert not any("/" in item.value or "&" in item.value for item in profile.vibes)


def test_profile_round_trip_preserves_multivalued_attributes() -> None:
    profile = make_profile()
    restored = ImageProfile.from_json(profile.to_json())
    assert restored == profile
    assert {item.value for item in restored.colors} == {"red", "blue"}
    assert {item.value for item in restored.vibes} == {"retro", "playful"}


def test_sqlite_persists_structured_profile(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    features = make_features(image)
    scores = (VibeScore("retro", 0.8),)
    with SQLiteAnalysisCache(tmp_path / "analysis.db", migrate_json=False) as cache:
        cache.set(image, features, scores)
        cache.set_profile(image, make_profile())
        restored = cache.get_profile(image)
    assert restored == make_profile()


def test_browser_filter_semantics_support_red_and_cool() -> None:
    from vibesorter.browser.server import _profile_matches

    profile = make_profile()
    assert _profile_matches(profile, {"colors": ["red"], "temperature": ["cool"]})
    assert not _profile_matches(profile, {"colors": ["green"]})


def test_folder_plan_review_apply_and_rollback(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")
    proposal = build_attribute_proposal(
        [make_result(image)], {image: make_profile()}, tmp_path / "Sorted"
    )
    decisions = review_folder_plan(proposal, accept_ids={1})
    assert validate_folder_plan(decisions) == ()
    applied = apply_folder_plan(decisions, confirm=True)
    assert Path(applied[0].destination).is_file()
    assert not image.exists()
    rollback_moves(applied)
    assert image.is_file()


def test_folder_plan_detects_conflicting_destination(tmp_path: Path) -> None:
    first = tmp_path / "one.jpg"
    second = tmp_path / "two.jpg"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    profiles = {first: make_profile(), second: make_profile()}
    proposal = build_attribute_proposal([make_result(first), make_result(second)], profiles, tmp_path / "Sorted")
    decisions = review_folder_plan(proposal, accept_ids={1, 2})
    blockers = validate_folder_plan(decisions)
    assert any("duplicate destination" in blocker for blocker in blockers) is False
    assert proposal.operations[0].destination != proposal.operations[1].destination
