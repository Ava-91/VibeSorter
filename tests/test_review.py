from pathlib import Path

from PIL import Image

from vibesorter.pipeline import analyze_image
from vibesorter.proposal import build_proposal
from vibesorter.review import (
    parse_selection,
    review_proposal,
    reviewed_from_dict,
    reviewed_to_dict,
)


def make_image(path: Path):
    Image.new("RGB", (12, 12), (30, 50, 90)).save(path)


def test_parse_selection_supports_ids_ranges_and_all():
    assert parse_selection("1,3-5", 6) == {1, 3, 4, 5}
    assert parse_selection("all", 3) == {1, 2, 3}


def test_review_can_accept_and_reject_individual_operations(tmp_path):
    paths = []
    for index in range(3):
        path = tmp_path / f"image{index}.jpg"
        make_image(path); paths.append(path)
    proposal = build_proposal([analyze_image(path) for path in paths], tmp_path / "Sorted")
    reviewed = review_proposal(proposal, accept_ids={1, 3}, reject_ids={2})
    assert [item.status for item in reviewed] == ["accepted", "rejected", "accepted"]


def test_rejected_operation_wins_over_vibe_acceptance(tmp_path):
    path = tmp_path / "image.jpg"
    make_image(path)
    proposal = build_proposal([analyze_image(path)], tmp_path / "Sorted")
    vibe = proposal.operations[0].vibe
    reviewed = review_proposal(proposal, accept_vibes={vibe}, reject_ids={1})
    assert reviewed[0].status == "rejected"


def test_reviewed_proposal_round_trips_with_metadata(tmp_path):
    path = tmp_path / "image.jpg"
    make_image(path)
    proposal = build_proposal([analyze_image(path)], tmp_path / "Sorted")
    reviewed = review_proposal(proposal, accept_ids={1})
    data = reviewed_to_dict(proposal, reviewed)

    restored = reviewed_from_dict(data)

    assert data["version"] == proposal.version
    assert data["output_root"] == proposal.output_root
    assert data["review"] == [{"id": 1, "status": "accepted"}]
    assert restored[0].operation == proposal.operations[0]
    assert restored[0].status == "accepted"
