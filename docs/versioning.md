# Version synchronization

VibeSorter currently uses a tested version-sync process rather than generating Rust configuration from Python metadata. When bumping a release version, update all of these declarations in the same pull request:

1. `pyproject.toml` — published Python package version.
2. `src/vibesorter/__init__.py` — runtime `__version__`, also used by the legacy CLI's `--version`.
3. `src-tauri/Cargo.toml` — Rust crate version.
4. `src-tauri/tauri.conf.json` — desktop bundle version.

The test `tests/test_version_consistency.py` compares all four values and runs with the Python test suite in CI. A release PR should include this test passing and should update `CHANGELOG.md` with the user-visible changes. Do not bump the desktop crate independently of the Python package.
