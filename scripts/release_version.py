"""Validate that a release tag agrees with every version declaration.

Final releases use ``vX.Y.Z`` and every file must say ``X.Y.Z``.

Release candidates use ``vX.Y.Z-rc.N``. The same release is spelled differently
by each ecosystem, so the mapping is explicit:

* Git tag:             ``v1.0.0-rc.1``
* Python (PEP 440):    ``1.0.0rc1``   (pyproject.toml, ``__version__``)
* Cargo / Tauri:       ``1.0.0-1``    (src-tauri/Cargo.toml, tauri.conf.json)

Cargo and Tauri use a numeric-only pre-release identifier because the MSI
(WiX) installer rejects non-numeric pre-release identifiers. No other
pre-release forms (alpha, beta, ...) are accepted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$")
PEP440_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?$")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(\d+))?$")
FORBIDDEN_NAME = "vibesorter"  # an unrelated project already owns this PyPI name


@dataclass(frozen=True)
class Release:
    base: tuple[int, int, int]
    rc: int | None

    @property
    def is_prerelease(self) -> bool:
        return self.rc is not None

    @property
    def python(self) -> str:
        base = ".".join(map(str, self.base))
        return base if self.rc is None else f"{base}rc{self.rc}"

    @property
    def semver(self) -> str:
        base = ".".join(map(str, self.base))
        return base if self.rc is None else f"{base}-{self.rc}"


def _from_match(match: re.Match[str] | None, what: str, value: str) -> Release:
    if match is None:
        raise ValueError(f"{what} {value!r} is not a supported version format")
    major, minor, patch, rc = match.groups()
    release = Release((int(major), int(minor), int(patch)), None if rc is None else int(rc))
    if release.rc == 0:
        raise ValueError(f"{what} {value!r}: release-candidate numbers start at 1")
    return release


def parse_tag(tag: str) -> Release:
    """Accept only ``vX.Y.Z`` and ``vX.Y.Z-rc.N``."""
    return _from_match(TAG_RE.match(tag), "tag", tag)


def parse_python(version: str) -> Release:
    return _from_match(PEP440_RE.match(version), "Python version", version)


def parse_semver(version: str) -> Release:
    return _from_match(SEMVER_RE.match(version), "Cargo/Tauri version", version)


def read_declarations(root: Path) -> dict[str, str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    init = (root / "src" / "vibesorter" / "__init__.py").read_text(encoding="utf-8")
    cargo = (root / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
    runtime = re.search(r'^__version__ = "([^"]+)"$', init, re.MULTILINE)
    crate = re.search(r'^version = "([^"]+)"$', cargo, re.MULTILINE)
    if runtime is None or crate is None:
        raise ValueError("could not find the runtime or Cargo version declaration")
    tauri = json.loads((root / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))["version"]
    return {
        "pyproject": project["version"],
        "runtime": runtime.group(1),
        "Cargo": crate.group(1),
        "Tauri": tauri,
        "name": project["name"],
    }


def declared_releases(declarations: dict[str, str]) -> dict[str, Release]:
    """Parse each declaration with its own ecosystem's syntax."""
    return {
        "pyproject": parse_python(declarations["pyproject"]),
        "runtime": parse_python(declarations["runtime"]),
        "Cargo": parse_semver(declarations["Cargo"]),
        "Tauri": parse_semver(declarations["Tauri"]),
    }


def check(root: Path, tag: str) -> list[str]:
    """Return a list of problems; empty means the tag and files agree."""
    problems: list[str] = []
    try:
        expected = parse_tag(tag)
    except ValueError as exc:
        return [str(exc)]
    declarations = read_declarations(root)
    if declarations["name"].casefold() == FORBIDDEN_NAME:
        problems.append(f"PyPI name {FORBIDDEN_NAME!r} is already used by an unrelated project")
    for label, spelled in (("pyproject", expected.python), ("runtime", expected.python),
                           ("Cargo", expected.semver), ("Tauri", expected.semver)):
        if declarations[label] != spelled:
            problems.append(f"{label} declares {declarations[label]!r} but tag {tag} requires {spelled!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="Release tag such as v1.0.0 or v1.0.0-rc.1")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    problems = check(args.root, args.tag)
    if problems:
        print("Release version validation failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    release = parse_tag(args.tag)
    kind = "release candidate" if release.is_prerelease else "final release"
    print(f"{args.tag} ({kind}): all version declarations agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
