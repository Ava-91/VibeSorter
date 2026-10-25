# Changelog

All notable development changes to VibeSorter are documented here.

## Unreleased

### Fixed — apply/rollback safety
- `review` now preserves `source_root` in the reviewed proposal. Previously `apply` refused every move of a reviewed proposal ("missing its source_root or output_root safety boundary"), so the documented `propose -> review -> apply` workflow could not move anything.
- Proposals now store absolute source paths. Previously history recorded relative paths, so `rollback` run from a different directory restored files into the wrong place and still reported success.
- `apply` now exits non-zero when a batch is refused (`unsafe_path` / `blocked`) and prints a Batch ID only when something was actually moved.
- Added end-to-end regression tests (`tests/test_apply_rollback_workflow.py`) using generated images, a library path with spaces and non-ASCII characters, dry-run, apply, and rollback from another working directory.

### Added — reliability
- Reusable temporary-image fixtures for tests.
- Classifier invariant coverage for score ordering and normalized confidence.
- Feature extraction contract coverage.
- Single-image pipeline contract coverage.
- Evaluation workflow coverage and documented test conventions.

### Added — benchmarking
- `vibesorter.benchmark` measurement engine for end-to-end local analysis.
- `BenchmarkResult` with image count, repeat count, elapsed time, throughput, and milliseconds per image.
- Stable dictionary serialization for machine-readable benchmark consumers.
- Benchmark tests, usage documentation, and a baseline comparison template.
- A documented CLI design for `vibesorter benchmark` with folder, recursion, repeat, and JSON options.

### Added — classifier evaluation
- `ClassificationDiagnostic` for winner, runner-up, margin, confidence, and ambiguity.
- A reusable `diagnose()` API for inspecting close decisions.
- A documented labelled JSONL example and measured classifier-improvement loop.
- Tests around diagnostic bounds and invalid ambiguity configuration.

### Added — explainability
- `vibesorter.explain.explain_image()` API.
- Structured explanations containing the winning vibe, confidence, decision margin, ambiguity flag, ranked scores, and extracted features.
- Serializable explanation output.
- Human and JSON output examples plus interpretation guidance.

### Added — vibe intelligence and scale
- Lightweight 2x2 spatial image features and center-vs-edge deltas.
- Overlap-aware multi-vibe selection while preserving a primary vibe.
- Offline nearest-centroid learned classifier with JSON persistence.
- Classifier comparison API for learned vs heuristic evaluation.
- SQLite analysis cache with automatic legacy JSON migration.
- Richer explain diagnostics with feature signals and selected secondary vibes.

### Development notes
- The benchmark and explain features are deliberately separated into reusable engines and documented CLI contracts so presentation can stay thin and future interfaces can reuse the same logic.
- Benchmarking remains read-only with respect to source images.
- Explainability describes the current feature-based heuristic; it does not claim semantic image understanding.
- The new learned classifier is an offline comparison path; the heuristic classifier remains the compatibility baseline.

## 0.8.1

### Added
- Cached library search with vibe, score, text-likelihood, path, brightness, saturation, contrast, and limit filters.
- Expanded CLI help and workflow examples.
- Persistent local analysis caching and incremental analysis support.
- Proposal, review, gallery, explicit apply, history, and rollback workflow.
- Duplicate and near-duplicate discovery.
- Classifier evaluation, confidence observations, and calibration support.

### Changed
- Project development direction moved toward practical large-library workflows while remaining a local-first vibe detector.
- Safety boundaries were clarified: analysis and planning commands are read-only, while filesystem operations require explicit confirmation.
