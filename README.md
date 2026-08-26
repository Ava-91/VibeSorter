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

Repeated library analysis can persist results in a local `.vibesorter/analysis.json` index. Each entry records the source file size and nanosecond modification time. If either changes, the image is analyzed again. Missing files can be pruned from the index.

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

For applications or scripts that need persistent local and incremental analysis:

```python
from vibesorter import analyze_library, analyze_library_stats

for result in analyze_library("path/to/photos"):
    print(result.path, result.best.name, result.best.score, result.cached)

print(analyze_library_stats("path/to/photos").to_dict())
```

The first run extracts features. Later runs reuse unchanged results. New files are analyzed, changed files invalidate their old entries, and missing files can be removed from the active cache.

## ⚡ Performance

VibeSorter is designed for large personal image collections rather than one-image demos. Lightweight feature extraction plus local incremental caching means repeated library operations can spend their time on new or changed images instead of the entire collection.

## 🗺️ Roadmap

### Core architecture

- [x] Single `src/vibesorter` package tree
- [x] Persistent local analysis index/cache
- [x] Incremental scanning and file identity tracking
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
