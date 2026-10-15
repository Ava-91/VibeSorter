from pathlib import Path

from vibesorter.operations import apply_reviewed
from vibesorter.proposal import MoveOperation
from vibesorter.review import ReviewedOperation


def reviewed_move(source: Path, destination: Path, confidence: float) -> tuple[ReviewedOperation, ...]:
    operation = MoveOperation(
        id=1,
        source=str(source),
        destination=str(destination),
        vibe="moody",
        score=0.8,
        confidence=confidence,
        text_likelihood=0.1,
    )
    return (ReviewedOperation(operation=operation, status="accepted"),)


def test_apply_blocks_low_confidence_before_filesystem_mutation(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "sorted" / "source.jpg"
    source.write_bytes(b"image")

    results = apply_reviewed(reviewed_move(source, destination, 0.59), confirm=True)

    assert results[0].status == "low_confidence"
    assert "below the 60% apply threshold" in results[0].detail
    assert source.read_bytes() == b"image"
    assert not destination.exists()


def test_dry_run_also_reports_low_confidence_as_blocked(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "sorted" / "source.jpg"
    source.write_bytes(b"image")

    results = apply_reviewed(reviewed_move(source, destination, 0.1), dry_run=True)

    assert results[0].status == "low_confidence"
    assert source.is_file()
    assert not destination.exists()


def test_apply_allows_confidence_at_threshold(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "sorted" / "source.jpg"
    source.write_bytes(b"image")

    results = apply_reviewed(reviewed_move(source, destination, 0.60), confirm=True)

    assert results[0].status == "moved"
    assert not source.exists()
    assert destination.read_bytes() == b"image"
