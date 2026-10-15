from pathlib import Path

from vibesorter.operations import apply_reviewed
from vibesorter.proposal import MoveOperation
from vibesorter.review import ReviewedOperation


def reviewed_move(source: Path, destination: Path, confidence: float, operation_id: int = 1) -> ReviewedOperation:
    operation = MoveOperation(operation_id, str(source), str(destination), "moody", 0.8, confidence, 0.1)
    return ReviewedOperation(operation=operation, status="accepted")


def test_apply_blocks_low_confidence_before_filesystem_mutation(tmp_path: Path) -> None:
    source, destination = tmp_path / "source.jpg", tmp_path / "sorted" / "source.jpg"
    source.write_bytes(b"image")
    result = apply_reviewed((reviewed_move(source, destination, 0.59),), confirm=True, source_root=tmp_path, output_root=tmp_path / "sorted")[0]
    assert result.status == "low_confidence"
    assert "below the 60% apply threshold" in result.detail
    assert source.read_bytes() == b"image"
    assert not destination.exists()


def test_dry_run_also_blocks_low_confidence(tmp_path: Path) -> None:
    source, destination = tmp_path / "source.jpg", tmp_path / "sorted" / "source.jpg"
    source.write_bytes(b"image")
    result = apply_reviewed((reviewed_move(source, destination, 0.1),), dry_run=True, source_root=tmp_path, output_root=tmp_path / "sorted")[0]
    assert result.status == "low_confidence"
    assert source.is_file() and not destination.exists()


def test_apply_allows_confidence_at_threshold(tmp_path: Path) -> None:
    source, destination = tmp_path / "source.jpg", tmp_path / "sorted" / "source.jpg"
    source.write_bytes(b"image")
    result = apply_reviewed((reviewed_move(source, destination, 0.60),), confirm=True, source_root=tmp_path, output_root=tmp_path / "sorted")[0]
    assert result.status == "moved"
    assert not source.exists()
    assert destination.read_bytes() == b"image"


def test_outside_source_blocks_entire_batch_before_mutation(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    valid, outside = library / "valid.jpg", tmp_path / "outside.jpg"
    valid.write_bytes(b"valid")
    outside.write_bytes(b"secret")
    output = tmp_path / "sorted"
    reviewed = (reviewed_move(valid, output / "valid.jpg", 0.9), reviewed_move(outside, output / "outside.jpg", 0.9, 2))
    results = apply_reviewed(reviewed, confirm=True, source_root=library, output_root=output)
    assert [result.status for result in results] == ["blocked", "unsafe_path"]
    assert valid.read_bytes() == b"valid" and outside.read_bytes() == b"secret"
    assert not output.exists()


def test_destination_traversal_is_rejected_without_mutation(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    source = library / "source.jpg"
    source.write_bytes(b"image")
    output = tmp_path / "sorted"
    destination = output / ".." / "escaped.jpg"
    result = apply_reviewed((reviewed_move(source, destination, 0.9),), confirm=True, source_root=library, output_root=output)[0]
    assert result.status == "unsafe_path"
    assert source.read_bytes() == b"image"
    assert not (tmp_path / "escaped.jpg").exists()


def test_source_symlink_is_rejected(tmp_path: Path) -> None:
    import pytest
    library = tmp_path / "library"
    library.mkdir()
    actual, link = tmp_path / "outside.jpg", library / "linked.jpg"
    actual.write_bytes(b"image")
    try:
        link.symlink_to(actual)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    destination = tmp_path / "sorted" / "linked.jpg"
    result = apply_reviewed((reviewed_move(link, destination, 0.9),), confirm=True, source_root=library, output_root=tmp_path / "sorted")[0]
    assert result.status == "unsafe_path"
    assert actual.read_bytes() == b"image" and not destination.exists()


def test_duplicate_destinations_block_all_moves(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    first, second = library / "a.jpg", library / "b.jpg"
    first.write_bytes(b"a")
    second.write_bytes(b"b")
    destination = tmp_path / "sorted" / "same.jpg"
    reviewed = (reviewed_move(first, destination, 0.9), reviewed_move(second, destination, 0.9, 2))
    results = apply_reviewed(reviewed, confirm=True, source_root=library, output_root=tmp_path / "sorted")
    assert [result.status for result in results] == ["unsafe_path", "unsafe_path"]
    assert first.read_bytes() == b"a" and second.read_bytes() == b"b"
    assert not destination.exists()
