# Changelog

All notable development changes to VibeSorter are documented here.

## Unreleased

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

### Development notes
- The benchmark and explain features are deliberately separated into reusable engines and documented CLI contracts so presentation can stay thin and future interfaces can reuse the same logic.
- Benchmarking remains read-only with respect to source images.
- Explainability describes the current feature-based heuristic; it does not claim semantic image understanding.

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
