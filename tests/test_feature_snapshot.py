from pathlib import Path

from PIL import Image

from vibesorter.features import extract_features


def test_extract_features_decodes_the_supplied_snapshot_not_the_mutated_path(tmp_path: Path):
    image = tmp_path / "snapshot.png"
    Image.new("RGB", (16, 16), (220, 30, 40)).save(image)
    snapshot = image.read_bytes()

    expected = extract_features(image, image_bytes=snapshot)

    Image.new("RGB", (16, 16), (20, 40, 220)).save(image)
    actual = extract_features(image, image_bytes=snapshot)
    current_file = extract_features(image)

    assert actual == expected
    assert actual != current_file
