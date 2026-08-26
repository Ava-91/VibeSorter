# Architecture

VibeSorter uses a `src` layout. The only importable application package is `src/vibesorter/`.

The repository root is reserved for project metadata, documentation, tests, and tooling. Runtime modules must not be added to a second root-level `vibesorter/` directory.

This keeps local execution and installed-package execution aligned and prevents a root checkout from accidentally shadowing the package selected by `pyproject.toml`.
