from pathlib import Path

from PIL import Image

from vibesorter.pipeline import analyze_image
from vibesorter.proposal import build_proposal, proposal_from_dict, proposal_to_dict


def make_image(path: Path, color: tuple[int, int, int]):
    Image.new("RGB", (16, 16), color).save(path)


def test_proposal_is_deterministic_and_read_only(tmp_path):
    first = tmp_path / "z.jpg"
    second = tmp_path / "a.jpg"
    make_image(first, (20, 30, 40))
    make_image(second, (220, 230, 240))
    before = {path: path.read_bytes() for path in (first, second)}

    results = [analyze_image(first), analyze_image(second)]
    proposal_a = build_proposal(results, tmp_path / "Sorted")
    proposal_b = build_proposal(list(reversed(results)), tmp_path / "Sorted")

    assert proposal_to_dict(proposal_a) == proposal_to_dict(proposal_b)
    assert [operation.id for operation in proposal_a.operations] == [1, 2]
    assert not (tmp_path / "Sorted").exists()
    assert {path: path.read_bytes() for path in (first, second)} == before


def test_proposal_handles_duplicate_filenames(tmp_path):
    left = tmp_path / "one" / "same.jpg"
    right = tmp_path / "two" / "same.jpg"
    left.parent.mkdir(); right.parent.mkdir()
    make_image(left, (20, 30, 40)); make_image(right, (21, 31, 41))

    proposal = build_proposal([analyze_image(right), analyze_image(left)], tmp_path / "Sorted")
    destinations = [operation.destination for operation in proposal.operations]
    assert len(destinations) == len(set(destinations))


def test_proposal_json_round_trip(tmp_path):
    path = tmp_path / "image.jpg"
    make_image(path, (100, 120, 140))
    proposal = build_proposal([analyze_image(path)], tmp_path / "Sorted")
    assert proposal_from_dict(proposal_to_dict(proposal)) == proposal
