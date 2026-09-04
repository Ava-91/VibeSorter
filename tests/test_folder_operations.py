from pathlib import Path

import pytest

from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.folder_operations import apply_folder_plan, review_folder_plan, rollback_moves, validate_folder_plan
from vibesorter.folder_planner import build_attribute_proposal
from vibesorter.pipeline import AnalysisResult
from vibesorter.profile import AttributeValue, ImageProfile
from vibesorter.vibes import VibeScore


def make_result(path: Path) -> AnalysisResult:
    features = ImageFeatures(path, (20, 40, 80), (0.6, .5, .5), .5, .5, .3, .1, .7, .05, .2, .3, .1, (ColorSample((20, 40, 80), 1.0),))
    score = VibeScore("Retro Blue", .8)
    return AnalysisResult(path, features, score, (score,), cached=True)


def make_profile() -> ImageProfile:
    return ImageProfile(media_type=AttributeValue("photograph", .95), colors=(AttributeValue("red", .8),), temperature=AttributeValue("cool", .8), saturation=AttributeValue("muted", .8), brightness=AttributeValue("dark", .8), vibes=(AttributeValue("retro", .7), AttributeValue("moody", .7)))


def test_review_keeps_unselected_operations_pending(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"; image.write_bytes(b"a")
    proposal = build_attribute_proposal([make_result(image)], {image: make_profile()}, tmp_path / "Sorted")
    assert review_folder_plan(proposal)[0].status == "pending"
    assert review_folder_plan(proposal, accept_ids={1})[0].status == "accepted"


def test_apply_requires_confirmation_and_supports_rollback(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"; image.write_bytes(b"a")
    proposal = build_attribute_proposal([make_result(image)], {image: make_profile()}, tmp_path / "Sorted")
    decisions = review_folder_plan(proposal, accept_ids={1})
    with pytest.raises(ValueError, match="explicit confirmation"):
        apply_folder_plan(decisions)
    applied = apply_folder_plan(decisions, confirm=True)
    assert not image.exists()
    assert Path(applied[0].destination).is_file()
    rollback_moves(applied)
    assert image.is_file()


def test_validation_blocks_existing_destinations(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"; image.write_bytes(b"a")
    proposal = build_attribute_proposal([make_result(image)], {image: make_profile()}, tmp_path / "Sorted")
    destination = Path(proposal.operations[0].destination); destination.parent.mkdir(parents=True); destination.write_bytes(b"existing")
    blockers = validate_folder_plan(review_folder_plan(proposal, accept_ids={1}))
    assert any("destination already exists" in blocker for blocker in blockers)
