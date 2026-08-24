# VibeSorter

> **Find the vibe of your image library.**
>
> VibeSorter is a local-first Python CLI that analyzes the visual character of images and groups them into aesthetic categories such as **Soft / Pastel**, **Dark / Moody**, **Retro Blue**, and **Black & White**.

It is built for people with *way too many pictures* who want to understand the visual mood of a collection before deciding how to organize it.

## ✨ What is the idea?

VibeSorter is not trying to be another generic photo manager.

The core idea is **visual-aesthetic organization**: instead of asking *"What is in this image?"*, it asks *"What does this image look and feel like?"*

For example, a large mixed folder might naturally turn into:

- 🎀 **Soft / Pastel** — pale, gentle, low-contrast imagery
- 🖤 **Dark / Moody** — dark, dramatic, low-light imagery
- 💙 **Retro Blue** — cool, blue-heavy imagery
- ❤️ **Red / Warm** — warm and red/orange-heavy imagery
- 🌓 **Black & White** — grayscale-dominant imagery
- 💚 **Green & Black** — green-heavy dark imagery
- 🌈 **Bright / Colorful** — vivid, high-saturation imagery

These are **visual vibes, not semantic labels**. VibeSorter currently does not try to read text, understand screenshots, recognize people, or determine what an image is about.

## 🚀 Why does this exist?

Because image libraries get ridiculous.

You might have thousands of screenshots, saved posts, wallpapers, artwork, memes, references, and random pictures scattered across folders. Manually sorting them by aesthetic is boring, while a cloud AI service is overkill for something that can be estimated from local visual features.

VibeSorter is an experiment in making that process **fast, local, explainable, and eventually useful**.

## 🧠 How it works

The current detector uses lightweight image features including:

- brightness
- saturation
- contrast
- warm/cool balance
- grayscale content
- dark/light ratios
- dominant color characteristics

It runs locally with Pillow and can analyze multiple images concurrently.

There is intentionally **no cloud AI API required** for the current detector.

## 📦 Installation

Python 3.10+ is required.

```bash
python -m pip install -e .
```

## 🖥️ CLI

### Discover images

```bash
vibesorter scan "path/to/photos"
```

### Preview detected vibes

```bash
vibesorter preview "path/to/photos"
```

Useful options:

```bash
vibesorter preview "path/to/photos" --workers 8
vibesorter preview "path/to/photos" --vibe "Dark / Moody"
vibesorter preview "path/to/photos" --min-score 0.70
vibesorter preview "path/to/photos" --top 10
vibesorter preview "path/to/photos" --json
```

### Analyze one image

```bash
vibesorter analyze "path/to/photo.jpg"
```

For machine-readable output:

```bash
vibesorter analyze "path/to/photo.jpg" --json
```

### Get vibe statistics

```bash
vibesorter stats "path/to/photos"
```

Or:

```bash
vibesorter stats "path/to/photos" --json
```

The CLI is intentionally read-only right now. **No images are moved, renamed, deleted, copied, or modified.**

## ⚡ Performance

VibeSorter is designed for large personal image collections rather than one-image demos.

Analysis uses concurrent workers and lightweight local features, so thousands of images can be processed without uploading them anywhere. The goal is to keep the pipeline simple enough that performance comes from efficient local processing rather than an expensive AI service.

## 🗺️ Roadmap

### Phase 1 — Foundation

- [x] Recursive image discovery
- [x] Local visual feature extraction
- [x] Vibe classification
- [x] Concurrent analysis
- [x] CLI reports and JSON output

### Phase 2 — Better understanding

- [ ] Improve vibe scoring and calibration
- [ ] Detect text-heavy / screenshot-like images separately
- [ ] Add duplicate / near-duplicate awareness
- [ ] Improve handling of unusual image formats

### Phase 3 — Actual organization

- [ ] Generate proposed folder structures
- [ ] Let users review proposed moves
- [ ] User-confirmed sorting
- [ ] Safe undo / rollback

### Phase 4 — Visual interface

- [ ] Image-grid preview
- [ ] Interactive vibe browser
- [ ] Desktop application
- [ ] Search and filtering

## 🔒 Privacy

VibeSorter is **local-first**.

Your images stay on your machine during analysis. The project does not require uploading your personal image library to a third-party AI service.

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