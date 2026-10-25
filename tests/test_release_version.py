"""Tag <-> version-declaration validation, including release-candidate spelling."""
from __future__ import annotations

import importlib.util
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("release_version", ROOT / "scripts" / "release_version.py")
release_version = importlib.util.module_from_spec(_spec)
sys.modules["release_version"] = release_version  # dataclasses need the module registered
_spec.loader.exec_module(release_version)


def _make_repo(root: Path, python: str, semver: str, name: str = "vibesorter-image-organizer") -> Path:
    (root / "src" / "vibesorter").mkdir(parents=True)
    (root / "src-tauri").mkdir()
    (root / "pyproject.toml").write_text(f'[project]\nname = "{name}"\nversion = "{python}"\n', encoding="utf-8")
    (root / "src" / "vibesorter" / "__init__.py").write_text(f'__version__ = "{python}"\n', encoding="utf-8")
    (root / "src-tauri" / "Cargo.toml").write_text(f'[package]\nname = "x"\nversion = "{semver}"\n', encoding="utf-8")
    (root / "src-tauri" / "tauri.conf.json").write_text(json.dumps({"version": semver}), encoding="utf-8")
    return root


def _rejects(func, value: str) -> bool:
    try:
        func(value)
    except ValueError:
        return True
    return False


def test_final_tag_requires_plain_version_everywhere(tmp_path):
    repo = _make_repo(tmp_path, "1.0.0", "1.0.0")
    assert release_version.check(repo, "v1.0.0") == []
    assert release_version.check(repo, "v1.0.1") != []


def test_release_candidate_uses_each_ecosystems_spelling(tmp_path):
    release = release_version.parse_tag("v1.0.0-rc.2")
    assert release.is_prerelease
    assert (release.python, release.semver) == ("1.0.0rc2", "1.0.0-2")
    repo = _make_repo(tmp_path, "1.0.0rc2", "1.0.0-2")
    assert release_version.check(repo, "v1.0.0-rc.2") == []


def test_final_tag_is_not_satisfied_by_release_candidate_files(tmp_path):
    repo = _make_repo(tmp_path, "1.0.0rc1", "1.0.0-1")
    problems = release_version.check(repo, "v1.0.0")
    assert len(problems) == 4


def test_mismatched_cargo_or_tauri_is_reported(tmp_path):
    repo = _make_repo(tmp_path, "1.0.0", "0.9.0")
    problems = release_version.check(repo, "v1.0.0")
    assert any("Cargo" in p for p in problems) and any("Tauri" in p for p in problems)


def test_unsupported_tags_are_rejected():
    for tag in ("1.0.0", "v1.0", "v1.0.0-beta.1", "v1.0.0-rc", "v1.0.0-rc.0", "v1.0.0-rc.1-x", "v1.0.0+build"):
        assert _rejects(release_version.parse_tag, tag), tag


def test_forbidden_pypi_name_is_refused(tmp_path):
    repo = _make_repo(tmp_path, "1.0.0", "1.0.0", name="VibeSorter")
    assert any("already used" in p for p in release_version.check(repo, "v1.0.0"))


def test_cli_exit_codes(tmp_path):
    repo = _make_repo(tmp_path, "1.0.0", "1.0.0")
    assert release_version.main(["--tag", "v1.0.0", "--root", str(repo)]) == 0
    assert release_version.main(["--tag", "v1.0.0-rc.1", "--root", str(repo)]) == 1


def test_repository_declarations_are_internally_consistent():
    declared = release_version.declared_releases(release_version.read_declarations(ROOT))
    assert len(set(declared.values())) == 1, declared
