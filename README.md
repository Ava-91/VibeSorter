# VibeSorter

> **Find the vibe of your image library.**
>
> VibeSorter is a local-first Python CLI that analyzes the visual character of images and groups them into overlapping aesthetic categories such as **Soft / Pastel**, **Dark / Moody**, **Retro Blue**, and **Black & White**.

It is built for people with *way too many pictures* who want to understand the visual mood of a collection before deciding how to organize it.

## ✨ What is the idea?

VibeSorter is not trying to be another generic photo manager. The core idea is **visual-aesthetic organization**: instead of asking *"What is in this image?"*, it asks *"What does this image look and feel like?"*

These are **visual vibes, not semantic labels**. VibeSorter currently does not try to read text, understand screenshots, recognize people, or determine what an image is about.

## 🧠 How it works

The detector uses lightweight local image features including brightness, saturation, contrast, warm/cool balance, grayscale content, dark/light ratios, dominant colors, and a small 2x2 spatial feature grid. Analysis runs through the single packaged `src/vibesorter/` implementation.

Repeated library analysis persists results in a local SQLite `.vibesorter/analysis.db` index. Each entry records the source file size and nanosecond modification time. If either changes, the image is analyzed again. Existing `.vibesorter/analysis.json` caches are imported automatically during migration.

A classification keeps the full ranked vibe scores. The strongest vibe remains the primary result for compatibility, while close secondary vibes can be selected when an image genuinely overlaps multiple aesthetics.

Classifier quality can be evaluated against a local human-labelled JSONL dataset. Vibe accuracy, per-vibe precision/recall, confusion matrices, raw confidence observations, and empirical calibration bins are available through the Python API. An offline nearest-centroid learned classifier is also available for comparison with the deterministic heuristic baseline.

## 📦 Installation

Python 3.10+ is required.

```bash
python -m pip install -e .
```

## 🖥️ CLI

```bash
vibesorter scan "path/to/photos"
vibesorter preview "path/to/photos"
vibesorter analyze "path/to/photo.jpg"
vibesorter stats "path/to/photos"
vibesorter search "path/to/photos" --vibe "Dark / Moody"
vibesorter search "path/to/photos" --min-score 0.80 --path "billie"
vibesorter search "path/to/photos" --min-brightness 0.65 --max-saturation 0.75 --limit 50
```

`search` reads the existing local analysis index without rescanning the folder or re-analyzing images. Secondary vibe scores are considered when searching by `--vibe`, so an image can match a meaningful non-primary aesthetic too.

Available search filters include:

- `--vibe` — exact vibe category, including a meaningful secondary vibe
- `--min-score` — minimum matching vibe score
- `--max-text-likelihood` — exclude text-heavy/screenshot-like images above a threshold
- `--path` — case-insensitive filename/path substring
- `--min/max-brightness`
- `--min/max-saturation`
- `--min/max-contrast`
- `--limit` — maximum number of returned results
- `--json` — machine-readable results for scripts and future interfaces

## ✨ DEVELOPMENT CHANGE

### VibeSorter 0.8.1 — a better CLI for a growing image library

VibeSorter is no longer just a detector you run once and forget about. The development focus has moved toward making the tool practical for **large, already-analyzed collections**.

#### 🔎 Cached image search

The new `search` command queries the local analysis index instead of touching every image again. You can filter thousands of analyzed images by:

- vibe
- minimum score
- filename or path
- text/screenshot likelihood
- brightness
- saturation
- contrast
- result limit

This keeps exploration fast while preserving the local-first design.

#### 🧠 Vibe intelligence

VibeSorter now retains overlapping vibe scores instead of pretending every image has one perfectly isolated aesthetic. Lightweight spatial features add regional context without introducing a heavyweight vision model.

The project also includes an offline nearest-centroid learned classifier and an evaluation API so data-driven classifier quality can be compared against the deterministic baseline.

#### 🖥️ `--help` got a real refresh

The CLI help now explains the command families, gives clearer descriptions for every command, documents important safety behavior, and includes a copy-paste workflow from **analyze → search → propose → review → gallery → apply → rollback**.

Try:

```bash
vibesorter --help
vibesorter search --help
vibesorter propose --help
```

#### 🔒 Safety remains the rule

Detection, statistics, duplicate checks, search, proposals, reviews, and galleries are read-only with respect to the source library. Actual filesystem changes still require explicit confirmation.

> **Development direction:** VibeSorter is intentionally staying a **vibe detector first**. Text-heavy images, screenshots, people, and semantic image understanding are not being treated as core classification targets yet.

## 🐍 Python API

For applications or scripts that need persistent local and incremental analysis:

```python
from vibesorter import analyze_library, analyze_library_stats

for result in analyze_library("path/to/photos"):
    print(result.path, result.best.name, result.best.score, result.cached)

print(analyze_library_stats("path/to/photos").to_dict())
```

Search uses the same query concepts independently of the CLI:

```python
from vibesorter.cache import AnalysisCache
from vibesorter.search import ImageQuery, search_cache

cache = AnalysisCache("path/to/photos/.vibesorter/analysis.db")
results = search_cache(cache, ImageQuery(vibe="Retro Blue", min_score=0.75, limit=25))
for result in results:
    print(result.path, result.best.name, result.best.score)
```

For evaluation:

```python
from vibesorter import ConfidenceCalibrator, collect_confidence_observations, evaluate_classifier, load_labels, LearnedClassifier

labels = load_labels("evaluation.jsonl")
metrics = evaluate_classifier(labels, LearnedClassifier.fit(labels))
print(metrics.to_dict())
```

For explainability:

```python
from vibesorter.explain import explain_image

print(explain_image("path/to/photo.jpg").to_dict())
```

## ⚡ Performance

VibeSorter is designed for large personal image collections rather than one-image demos. Lightweight feature extraction plus local incremental caching means repeated library operations can spend their time on new or changed images instead of the entire collection. Cached search takes this one step further: once a library has been analyzed, filters operate on stored results without touching image pixels.

## 🗺️ Roadmap

### Core architecture

- [x] Single `src/vibesorter` package tree
- [x] Persistent local SQLite analysis index
- [x] Incremental scanning and file identity tracking
- [x] Classifier evaluation and confidence calibration
- [x] Offline learned classifier comparison path

### Detection

- [x] Recursive image discovery
- [x] Local visual feature extraction
- [x] Vibe classification
- [x] Overlapping multi-vibe scores
- [x] Lightweight spatial features
- [x] Duplicate / near-duplicate awareness
- [ ] Improve handling of unusual image formats
- [ ] Detect text-heavy / screenshot-like images separately

### Organization

- [x] Concurrent analysis
- [x] CLI reports and JSON output
- [x] Generate proposed folder structures
- [x] Let users review proposed moves
- [x] User-confirmed sorting
- [x] Safe undo / rollback

### Interface

- [x] Image-grid preview
- [x] Image search and filtering
- [x] Explainable classification diagnostics
- [ ] Interactive vibe browser
- [ ] Desktop application

## 🔒 Privacy

VibeSorter is **local-first**. Your images stay on your machine during analysis. The project does not require uploading your personal image library to a third-party AI service.

## 🛠️ Tech

- Python
- Pillow
- `argparse`
- `ThreadPoolExecutor`
- SQLite local analysis cache
- Deterministic feature-based classifier
- Offline nearest-centroid learned classifier
- Local evaluation and confidence calibration

## 📄 License

See [LICENSE](LICENSE).

---

VibeSorter is an ongoing experiment in **organizing images by how they feel, not just what they contain.**
