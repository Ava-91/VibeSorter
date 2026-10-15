import tempfile
import unittest
from pathlib import Path

import pytest

from vibesorter.scanner import find_images


class ScannerTests(unittest.TestCase):
    def test_find_images_recursively_and_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            (root / "one.JPG").touch()
            (nested / "two.png").touch()
            (nested / "notes.txt").touch()

            expected = sorted(
                [root / "one.JPG", nested / "two.png"],
                key=lambda path: str(path).casefold(),
            )
            self.assertEqual(find_images(root), expected)

    def test_find_images_can_disable_recursion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            (root / "one.jpg").touch()
            (nested / "two.jpg").touch()

            self.assertEqual(find_images(root, recursive=False), [root / "one.jpg"])

    def test_find_images_excludes_vibesorter_managed_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.jpg"
            original.touch()
            managed = root / ".vibesorter" / "thumbnails"
            managed.mkdir(parents=True)
            (managed / "generated.jpg").touch()
            nested_managed = root / "nested" / ".VIBESORTER" / "thumbnails"
            nested_managed.mkdir(parents=True)
            (nested_managed / "generated-again.png").touch()
            (root / "nested").mkdir(exist_ok=True)
            (root / "nested" / "real.jpg").touch()

            expected = sorted(
                [original, root / "nested" / "real.jpg"],
                key=lambda path: str(path).casefold(),
            )
            self.assertEqual(find_images(root), expected)
            # Repeated scans remain stable; generated thumbnails are never
            # promoted into the source image set.
            self.assertEqual(find_images(root), expected)

    def test_find_images_rejects_missing_folder(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            find_images(Path(directory) / "missing")

    def test_find_images_rejects_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "image.jpg"
            file_path.touch()

            with self.assertRaises(NotADirectoryError):
                find_images(file_path)


if __name__ == "__main__":
    unittest.main()



def test_scanner_includes_hidden_user_folders_and_unicode_names(tmp_path: Path):
    hidden = tmp_path / ".my-private-album"
    hidden.mkdir()
    image = hidden / "雪-照片_日本.JPG"
    image.touch()

    assert find_images(tmp_path) == [image]


def test_scanner_excludes_symlinked_files_and_directories(tmp_path: Path):
    root = tmp_path / "library"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "photo.jpg"
    target.touch()
    try:
        (root / "linked.jpg").symlink_to(target)
        (root / "linked-directory").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable on this platform")

    assert find_images(root) == []


def test_scanner_raises_on_walk_permission_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "library"
    root.mkdir()

    def failing_walk(_root, *, followlinks, onerror):
        onerror(PermissionError("simulated directory permission error"))
        return iter(())

    monkeypatch.setattr("vibesorter.scanner.os.walk", failing_walk)
    with pytest.raises(PermissionError, match="simulated directory permission error"):
        find_images(root)



def test_scanner_handles_unicode_and_long_nested_paths(tmp_path: Path):
    nested = tmp_path / ("a" * 60) / ("b" * 60)
    nested.mkdir(parents=True)
    image = nested / "写真-portrait.png"
    image.touch()

    assert find_images(tmp_path) == [image]
