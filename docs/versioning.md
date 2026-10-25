# Version synchronization

VibeSorter currently uses a tested version-sync process rather than generating Rust configuration from Python metadata. When bumping a release version, update all of these declarations in the same pull request:

1. `pyproject.toml` — published Python package version.
2. `src/vibesorter/__init__.py` — runtime `__version__`, also used by the legacy CLI's `--version`.
3. `src-tauri/Cargo.toml` — Rust crate version.
4. `src-tauri/tauri.conf.json` — desktop bundle version.

The test `tests/test_version_consistency.py` compares all four values and runs with the Python test suite in CI. A release PR should include this test passing and should update `CHANGELOG.md` with the user-visible changes. Do not bump the desktop crate independently of the Python package.

## Release tags and release candidates

The tag-driven release workflow runs `scripts/release_version.py --tag <tag>` and refuses to continue unless the tag agrees with all four declarations. Only two tag shapes are accepted:

| Tag | `pyproject.toml` / `__version__` (PEP 440) | `Cargo.toml` / `tauri.conf.json` (SemVer) |
| --- | --- | --- |
| `v1.0.0` (final) | `1.0.0` | `1.0.0` |
| `v1.0.0-rc.1` (candidate) | `1.0.0rc1` | `1.0.0-1` |

Cargo and Tauri use a numeric-only pre-release identifier because the MSI (WiX) installer rejects non-numeric ones. Other pre-release forms (`-beta`, `-alpha`, `-rc` without a number) are rejected. The tagged commit must also be reachable from `main`, and a release candidate publishes only a **draft, pre-release** GitHub release.

To cut a candidate, a commit on `main` must first change the four declarations to the candidate spelling above; the final `v1.0.0` then needs a commit that restores plain `1.0.0`. `tests/test_release_version.py` covers the mapping, and `tests/test_version_consistency.py` accepts either spelling as long as all four name the same release.

Not yet verified: that the MSI/NSIS bundlers accept a `1.0.0-1` Tauri version. Check this on the first candidate build before relying on it.
