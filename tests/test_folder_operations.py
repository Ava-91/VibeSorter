from pathlib import Path

import pytest

from vibesorter.features import ColorSample, ImageFeatures
from vibesorter.folder_operations import (
    apply_folder_plan,
    review_folder_plan,
    rollback_moves,
    validate_folder_plan,
)
from vibesorter.folder_planner import build_attribute_proposal
from vibesorter.pipeline import AnalysisResult
from vibesorter.profile import AttributeValue, ImageProfile
from vibesorter.vibes import VibeScore


def make_result(path: Path) -> AnalysisResult:
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
    score = VibeScore("Retro Blue", 0.8)
    return AnalysisResult(path, features, score, (score,), cached=True)


def make_profile() -> ImageProfile:
    return ImageProfile(
        media_type=AttributeValue("photograph", 0.95),
        colors=(AttributeValue("red", 0.8),),
        temperature=AttributeValue("cool", 0.8),
        saturation=AttributeValue("muted", 0.8),
        brightness=AttributeValue("dark", 0.8),
        vibes=(AttributeValue("retro", 0.7), AttributeValue("moody", 0.7)),
    )


def test_review_keeps_unselected_operations_pending(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"
    image.write_bytes(b"a")
    proposal = build_attribute_proposal([make_result(image)], {image: make_profile()}, tmp_path / "Sorted")
    assert review_folder_plan(proposal)[0].status == "pending"
    assert review_folder_plan(proposal, accept_ids={1})[0].status == "accepted"


def test_apply_requires_confirmation_and_supports_rollback(tmp_path: Path) -> None:
    image = tmp_path / "a.jpg"
    image.write_bytes(b"a")
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
    image = tmp_path / "a.jpg"
    image.write_bytes(b"a")
    proposal = build_attribute_proposal([make_result(image)], {image: make_profile()}, tmp_path / "Sorted")
    destination = Path(proposal.operations[0].destination)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")
    blockers = validate_folder_plan(review_folder_plan(proposal, accept_ids={1}))
    assert any("destination already exists" in blocker for blocker in blockers)


def test_apply_rolls_back_completed_moves_when_later_move_fails(tmp_path: Path, monkeypatch) -> None:
    from vibesorter import folder_operations

    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    results = [make_result(first), make_result(second)]
    proposal = build_attribute_proposal(results, {first: make_profile(), second: make_profile()}, tmp_path / "Sorted")
    decisions = review_folder_plan(proposal, accept_ids={1, 2})
    real_move = folder_operations.shutil.move
    calls = 0

    def fail_second_move(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second move failure")
        return real_move(source, destination)

    monkeypatch.setattr(folder_operations.shutil, "move", fail_second_move)
    with pytest.raises(OSError, match="simulated second move failure"):
        apply_folder_plan(decisions, confirm=True)
    assert first.is_file()
    assert second.is_file()
    assert not (tmp_path / "Sorted").exists() or not list((tmp_path / "Sorted").rglob("*.jpg"))


def test_apply_rolls_back_moves_when_journal_commit_fails(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"photo")
    proposal = build_attribute_proposal([make_result(image)], {image: make_profile()}, tmp_path / "Sorted")
    decisions = review_folder_plan(proposal, accept_ids={1})
    journal = tmp_path / "history" / "batch.json"
    real_write_text = Path.write_text

    def fail_journal_temp(path, *args, **kwargs):
        if path == journal.with_name(journal.name + ".tmp"):
            raise OSError("simulated journal write failure")
        return real_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_journal_temp)
    with pytest.raises(OSError, match="simulated journal write failure"):
        apply_folder_plan(decisions, confirm=True, journal_path=journal)
    assert image.is_file()
    assert not journal.exists()
