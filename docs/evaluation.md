# Classifier evaluation

VibeSorter can evaluate its deterministic heuristic classifier against a human-labelled JSONL dataset without modifying or uploading source images.

## 1. Create a representative label sample

For a real image library, use the built-in sampler to create a deterministic subset rather than manually collecting paths:

```bash
vibesorter sample-labels "E:\\Ava files\\Pictures\\Billie Eilish" --count 150 --output labels.jsonl
```

The sampler discovers supported image files, selects evenly distributed paths from the sorted file list, and writes only paths plus blank labels. Re-running against an unchanged folder produces the same sample. It never copies or modifies source images.

Use `--no-recursive` if only the top-level folder should be considered. The output defaults to `labels.jsonl` when `--output` is omitted.

Open `labels.jsonl` in a text editor and fill every empty `label` with the vibe that a human believes best describes that image. Do not evaluate the template while labels are blank: `vibesorter evaluate` requires valid vibe names.

Include different lighting, color palettes, subjects, crops, and borderline cases. A representative sample is more useful than choosing only easy examples.

Each completed JSONL line has this shape:

```json
{"path":"E:/Ava files/Pictures/Billie Eilish/example.jpg","label":"Retro Blue"}
```

The label must be one of:

- `Retro Blue`
- `Red / Warm`
- `Green & Black`
- `Black & White`
- `Soft / Pastel`
- `Dark / Moody`
- `Bright / Colorful`

Do not commit private images or a private library's labels file to the repository.

## 2. Run the evaluation

```bash
vibesorter evaluate labels.jsonl
```

For machine-readable output:

```bash
vibesorter evaluate labels.jsonl --json > evaluation.json
```

Use `--bins` to change the number of confidence calibration bins (10 by default).

The command is read-only. It extracts features from the referenced local images and does not rename, move, rewrite, or upload them.

## 3. Read the report

### Accuracy

Overall fraction of labelled images whose predicted primary vibe matches the human label. Accuracy is useful as a headline metric, but it can hide weak performance on less frequent vibes.

### Precision, recall, and F1

Each vibe includes support, precision, recall, and F1:

- **Precision:** when VibeSorter predicts this vibe, how often is it correct?
- **Recall:** of the images humans labelled with this vibe, how many did VibeSorter find?
- **F1:** harmonic mean of precision and recall.
- **Support:** number of human-labelled examples for the vibe.

Zero-support classes are reported with zero precision/recall/F1 so the report stays explicit about missing evidence.

### Confusion matrix

The matrix is indexed as `actual -> predicted`. Concentrated off-diagonal counts reveal systematic confusion, such as muted blue images repeatedly being called Soft / Pastel.

### Ambiguity

An image is counted as ambiguous when its prediction does not satisfy VibeSorter's existing confidence thresholds. This is intentionally separate from correctness: a low-confidence correct prediction is still evidence of uncertainty.

### Calibration error

The confidence calibration error is the confidence-weighted gap between reported confidence and observed correctness across bins. Lower is better. Treat it as a diagnostic rather than a replacement for accuracy and per-vibe metrics.

## 4. How to decide whether the classifier needs a fix

Do not change a weight because one image looks surprising. Look for repeated patterns in the labelled set:

1. Identify the largest confusion pairs.
2. Check precision/recall/F1 and support for both vibes.
3. Inspect ambiguous cases with `vibesorter explain IMAGE`.
4. Look for a feature or rule that explains the repeated error.
5. Add a regression fixture for the failure pattern.
6. Make the smallest evidence-backed scoring change.
7. Re-run the full test suite and the same labelled evaluation set.

A small or imbalanced sample should not be treated as proof of general classifier quality. The benchmark is a feedback loop for this project's real image library, not a claim of universal vision performance.
