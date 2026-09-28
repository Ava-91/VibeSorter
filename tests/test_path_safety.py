import os
from pathlib import Path

from vibesorter.path_safety import canonical_path, same_path


def test_canonical_path_resolves_equivalent_paths(tmp_path: Path):
    target = tmp_path / "sorted" / "image.png"
    assert canonical_path(target) == canonical_path(target.parent / ".." / target.parent.name / target.name)
    assert same_path(target, target.parent / ".." / target.parent.name / target.name)


def test_canonical_path_uses_platform_case_rules(tmp_path: Path, monkeypatch):
    target = tmp_path / "Image.png"
    monkeypatch.setattr(os.path, "normcase", lambda value: value.casefold())
    assert same_path(target, tmp_path / "image.png")
