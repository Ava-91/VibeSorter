# Classifier evaluation

VibeSorter can evaluate its deterministic heuristic classifier against a human-labelled JSONL dataset without modifying or uploading source images.

## 1. Prepare a representative assisted-labeling session

For a real image library, let VibeSorter select difficult examples and show the actual images locally:

```bash
vibesorter label "E:\\Ava files\\Pictures\\Billie Eilish" --count 150 --output labels.jsonl
```

The command incrementally indexes the folder into its local SQLite cache, then starts a local browser at `http://127.0.0.1:8765/label`. No source images are copied or uploaded. If the cache already exists, unchanged images are reused instead of re-analyzed.

By default, candidates are ordered with ambiguous and lower-confidence predictions first. Use `--all-order` when you want deterministic path order instead. Use `--db` to point at an existing analysis database, and `--host`/`--port` to change the local server address.

### Human-in-the-loop controls

For each image, VibeSorter shows:

- the actual local image
- its predicted vibe
- confidence and ambiguity
- the strongest competing vibe scores

Then make one quick decision:

- **Enter:** accept VibeSorter's prediction
- **1–7:** correct it to a specific vibe
- **S:** skip it for later
- **U:** undo the last decision

Every accepted/corrected decision is written immediately to the JSONL file, so closing the browser or stopping the server does not discard completed labels. Starting the same session again resumes from already-labelled paths. Skipped images remain unlabelled and can be reviewed later.

If you previously ran `sample-labels` and already have a JSONL file containing records such as `{"path":"...","label":""}`, you can pass that same file to `label`. Empty labels are treated as pending work; they are not errors. Once a decision is saved, the corresponding record becomes a completed human label. Invalid non-empty labels are still rejected.

The output records the human decision separately from the classifier proposal, for example:

```json
{"path":"E:/Ava files/Pictures/Billie Eilish/example.jpg","label":"Dark / Moody","source":"human","prediction":"Soft / Pastel","confidence":0.41}
```

The `label` field is the ground-truth decision used by evaluation. The `prediction` and `confidence` fields are audit information and do not become ground truth automatically.

The label must be one of:

- `Retro Blue`
- `Red / Warm`
- `Green & Black`
- `Black & White`
- `Soft / Pastel`
- `Dark / Moody`
- `Bright / Colorful`

Do not commit private images or a private library's labels file to the repository.

### Legacy deterministic sampler

`sample-labels` remains available when you specifically want a blank path-only template:

```bash
vibesorter sample-labels "E:\\Ava files\\Pictures\\Billie Eilish" --count 150 --output labels.jsonl
```

It discovers supported image files, selects evenly distributed paths from the sorted file list, and writes blank labels. It is intentionally manual; the `label` command is the recommended workflow for classifier evaluation. A template from this command can also be used directly as the starting point for `label`.

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
