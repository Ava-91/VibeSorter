from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _match(pattern: str, content: str) -> str:
    match = re.search(pattern, content, re.MULTILINE)
    assert match is not None, f"version declaration not found for pattern: {pattern}"
    return match.group(1)


def test_python_package_and_desktop_versions_stay_in_sync() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    cargo = (ROOT / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    tauri = json.loads((ROOT / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))
    package_init = (ROOT / "src" / "vibesorter" / "__init__.py").read_text(encoding="utf-8")

    versions = {
        "Python project": _match(r'^version = "([^"]+)"$', pyproject),
        "Rust desktop crate": _match(r'^version = "([^"]+)"$', cargo),
        "Tauri bundle": tauri["version"],
        "Python runtime": _match(r'^__version__ = "([^"]+)"$', package_init),
    }
    assert len(set(versions.values())) == 1, f"version mismatch: {versions}"
