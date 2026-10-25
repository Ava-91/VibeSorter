from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("release_version", ROOT / "scripts" / "release_version.py")
release_version = importlib.util.module_from_spec(_spec)
sys.modules["release_version"] = release_version  # dataclasses need the module registered
_spec.loader.exec_module(release_version)


def test_python_package_and_desktop_versions_stay_in_sync() -> None:
    """All four declarations name the same release, each in its own ecosystem's syntax."""
    declarations = release_version.read_declarations(ROOT)
    parsed = release_version.declared_releases(declarations)
    assert len(set(parsed.values())) == 1, f"version mismatch: {declarations}"
