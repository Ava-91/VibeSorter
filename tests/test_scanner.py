import tempfile
import unittest
from pathlib import Path

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
