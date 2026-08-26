# VibeSorter

> **Find the vibe of your image library.**
>
> VibeSorter is a local-first Python CLI that analyzes the visual character of images and groups them into aesthetic categories such as **Soft / Pastel**, **Dark / Moody**, **Retro Blue**, and **Black & White**.

It is built for people with *way too many pictures* who want to understand the visual mood of a collection before deciding how to organize it.

## ✨ What is the idea?

VibeSorter is not trying to be another generic photo manager. The core idea is **visual-aesthetic organization**: instead of asking *"What is in this image?"*, it asks *"What does this image look and feel like?"*

These are **visual vibes, not semantic labels**. VibeSorter currently does not try to read text, understand screenshots, recognize people, or determine what an image is about.

## 🧠 How it works

The detector uses lightweight local image features including brightness, saturation, contrast, warm/cool balance, grayscale content, dark/light ratios, and dominant colors. Analysis runs through the single packaged `src/vibesorter/` implementation.

For repeated library analysis, the Python API can persist results in a local `.vibesorter/analysis.json` index. The cache is versioned, written atomically, and ignored when it is malformed or incompatible.

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
```

The analysis commands are read-only with respect to source images.

## 🐍 Python API

For applications or scripts that need persistent local analysis:

```python
from vibesorter import analyze_library

for result in analyze_library("path/to/photos"):
    print(result.path, result.best.name, result.best.score, result.cached)
```

The first run extracts features. Later runs can reuse cached results for the same image paths. Incremental file identity checks are the next step in the roadmap.

## ⚡ Performance

VibeSorter is designed for large personal image collections rather than one-image demos. Analysis uses concurrent workers and lightweight local features. Persistent local analysis data prevents callers using the library API from repeatedly decoding unchanged images.

## 🗺️ Roadmap

### Core architecture

- [x] Single `src/vibesorter` package tree
- [x] Persistent local analysis index/cache
- [ ] Incremental scanning and file identity tracking
- [ ] Classifier evaluation and confidence calibration

### Detection

- [x] Recursive image discovery
- [x] Local visual feature extraction
- [x] Vibe classification
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
- [ ] Image search and filtering
- [ ] Interactive vibe browser
- [ ] Desktop application

## 🔒 Privacy

VibeSorter is **local-first**. Your images stay on your machine during analysis. The project does not require uploading your personal image library to a third-party AI service.

## 🛠️ Tech

- Python
- Pillow
- `argparse`
- `ThreadPoolExecutor`
- Local JSON analysis cache
- CLI-first workflow

## 📄 License

See [LICENSE](LICENSE).

---

VibeSorter is an ongoing experiment in **organizing images by how they feel, not just what they contain.**
