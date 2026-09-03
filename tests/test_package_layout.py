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
    assert all(path.parent == root / "src" / "vibesorter" for path in package_files)


def test_project_metadata_uses_src_layout() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'where = ["src"]' in pyproject
    assert 'vibesorter = "vibesorter.entrypoint:main"' in pyproject
