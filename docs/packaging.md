# Python distribution naming and publishing

The import package and console commands remain `vibesorter`, but the distribution metadata uses `vibesorter-image-organizer`. The name `vibesorter` is already published on PyPI by an unrelated LLM-based array-sorting project, so VibeSorter must not publish a wheel or source archive under that name.

## Before publishing to PyPI

- [ ] Confirm the candidate project name is available and reserve it under the maintainer's PyPI account. A public project-page 404 alone is not proof that a name is unreserved.
- [ ] Build both wheel and source archive with `python -m build --outdir dist`.
- [ ] Install the wheel in a clean virtual environment and verify `import vibesorter`, `vibesorter --version`, and the browser/desktop entry points.
- [ ] Configure PyPI Trusted Publishing only after the final project name is reserved.
- [ ] Keep the GitHub release pipeline separate from PyPI publishing until these steps are complete.

For development from a checkout, use `python -m pip install -e ".[dev]"`. The distribution rename does not rename the `src/vibesorter` import package.