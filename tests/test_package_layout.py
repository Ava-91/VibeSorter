from __future__ import annotations

from pathlib import Path


def test_package_has_single_source_tree() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "src" / "vibesorter").is_dir()
    assert not (root / "vibesorter").exists()


def test_packaged_modules_live_under_src() -> None:
    root = Path(__file__).resolve().parents[1]
    package_files = list((root / "src" / "vibesorter").glob("*.py"))
    assert package_files
    assert all(path.parent.name == "vibesorter" for path in package_files)
