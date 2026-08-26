# VibeSorter

> **Find the vibe of your image library.**
>
> VibeSorter is a local-first Python CLI that analyzes the visual character of images and groups them into aesthetic categories such as **Soft / Pastel**, **Dark / Moody**, **Retro Blue**, and **Black & White**.

It is built for people with *way too many pictures* who want to understand the visual mood of a collection before deciding how to organize it.

## ✨ What is the idea?

VibeSorter is not trying to be another generic photo manager.

The core idea is **visual-aesthetic organization**: instead of asking *"What is in this image?"*, it asks *"What does this image look and feel like?"*

These are **visual vibes, not semantic labels**. VibeSorter currently does not try to read text, understand screenshots, recognize people, or determine what an image is about.

## 🧠 How it works

The detector uses lightweight local image features including brightness, saturation, contrast, warm/cool balance, grayscale content, dark/light ratios, and dominant colors. Analysis runs through the packaged `src/vibesorter/` implementation.

The repository deliberately uses a single `src` package tree so the code used during development and installation stays consistent.

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

The CLI is read-only during analysis. **No images are moved, renamed, deleted, copied, or modified by scan/preview/analyze/stats.**

## ⚡ Performance

VibeSorter is designed for large personal image collections rather than one-image demos. Analysis uses concurrent workers and lightweight local features, while later commands can build on persistent local analysis data instead of repeatedly decoding the same images.

## 🗺️ Roadmap

### Phase 1 — Foundation

- [x] Recursive image discovery
- [x] Local visual feature extraction
- [x] Vibe classification
- [x] Concurrent analysis
- [x] CLI reports and JSON output
- [x] Single `src/vibesorter` package tree
- [ ] Persistent local analysis index
- [ ] Incremental scanning
- [ ] Classifier evaluation and confidence calibration

### Phase 2 — Better understanding

- [ ] Improve vibe scoring and calibration
- [ ] Detect text-heavy / screenshot-like images separately
- [x] Duplicate / near-duplicate awareness
- [ ] Improve handling of unusual image formats

### Phase 3 — Actual organization

- [x] Generate proposed folder structures
- [x] Let users review proposed moves
- [x] User-confirmed sorting
- [x] Safe undo / rollback

### Phase 4 — Visual interface

- [x] Image-grid preview
- [ ] Interactive vibe browser
- [ ] Desktop application
- [ ] Search and filtering

## 🔒 Privacy

VibeSorter is **local-first**. Your images stay on your machine during analysis. The project does not require uploading your personal image library to a third-party AI service.

## 🛠️ Tech

- Python
- Pillow
- `argparse`
- `ThreadPoolExecutor`
- Local image analysis
- CLI-first workflow

## 📄 License

See [LICENSE](LICENSE).

---

VibeSorter is an ongoing experiment in **organizing images by how they feel, not just what they contain.**
