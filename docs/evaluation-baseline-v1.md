# Classifier evaluation baseline — protocol v1

**Status:** protocol defined; the human-labelled reference set must be populated and reviewed before reporting a release-quality accuracy claim.

## Ground-truth rule

Only labels assigned by a human reviewer are ground truth. Never copy a classifier prediction into the label field, and never generate labels from the model under test. Synthetic images and unit-test fixtures are useful for regression testing, but are not a substitute for a representative human-labelled evaluation set.

## Dataset versioning

Store a frozen release of the reference set under `datasets/evaluation/v1/` and commit the exact image manifest and JSONL labels together. Keep original image bytes unchanged. Record the dataset version, image SHA-256, labeler, label date, and any adjudication in a companion manifest. A change to image membership or a human label requires a new dataset revision and a short changelog entry; do not silently overwrite the reference set used for a published score.

The evaluator's minimal JSONL schema is one object per image:

    {"path": "relative/or/absolute/image.png", "label": "moody"}

The `label` must be one of the canonical v2.0 vibe values: `retro`, `dreamy`, `soft`, `moody`, `minimal`, `cozy`, `cinematic`, `playful`, `edgy`, or `romantic`. Compound legacy labels such as `Retro Blue` are invalid.

## Annotation protocol

1. Sample images across the intended use cases, image sources, aspect ratios, brightness levels, and photographic/illustration/screenshot/graphic media types. Avoid selecting only images that look easy for the current classifier.
2. Have a reviewer inspect each image without seeing the model prediction. Assign the single dominant vibe from the canonical vocabulary. Use the visible image, not filename, folder name, or an existing prediction.
3. When multiple vibes are plausible, choose the strongest overall impression and mark the case as ambiguous in the companion manifest. For disagreements, record both labels and an adjudicated label with a short rationale.
4. Keep a holdout set separate from any images used to tune heuristic weights or fit the learned classifier.
5. Before evaluating, validate the labels, verify image checksums, and review the class distribution. Report per-class support so absent or underrepresented classes are obvious.

## Multi-label evaluation

The single-label JSONL schema above measures the dominant vibe only. It does not measure the product's multi-vibe behavior. For that, maintain a separate human-reviewed JSONL file with one record per image and a non-empty `labels` list, for example:

    {"path": "relative/or/absolute/image.png", "labels": ["dreamy", "soft"]}

Every label must be a unique canonical v2.0 vibe value. The evaluation functions are implemented, but release-quality claims still require the real human-labeled dataset to be populated and reviewed; synthetic unit fixtures do not count as benchmark evidence. Annotators should select all vibes that genuinely apply under the written annotation guide, without seeing model output. Keep the multi-label set and its holdout split fixed and versioned independently of the single-dominant-label set.

Use `load_multilabel_labels` and `evaluate_multilabel_labels` from `vibesorter.evaluation` to report exact-set match, micro precision/recall/F1, macro F1, and per-vibe support/precision/recall/F1. Report the selector threshold and margin with every result. These are benchmark metrics, not calibrated probabilities; do not tune thresholds on the holdout set.

## Reproducible evaluation

Run against the committed labels file with the same Python/package version used for the release:

    vibesorter evaluate datasets/evaluation/v1/labels.jsonl --json

The report includes overall accuracy, per-class precision/recall/F1/support, the confusion matrix, ambiguous prediction count/rate, and confidence calibration error. Record the dataset revision, command, software commit, and full JSON report together. Compare reports only when the label protocol and dataset revision are the same.

## Current limitation

This repository currently defines the protocol and validates the label format; it does not claim a release-quality benchmark until a representative human-labelled set and its image manifest are committed. A passing unit test is not evidence of real-world classifier accuracy.
