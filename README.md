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

A classification keeps the full ranked vibe scores. The strongest vibe remains the primary result for compatibility, while close secondary vibes can be selected when an image genuinely overlaps multiple aesthetics.

Repeated library analysis persists results in a local SQLite `.vibesorter/analysis.db` index. Existing `.vibesorter/analysis.json` caches are imported automatically during migration. Each entry records source file size and nanosecond modification time, so changed images are analyzed again.

Classifier quality can be evaluated against a local human-labelled JSONL dataset. The project also includes an offline nearest-centroid learned classifier so data-driven models can be compared with the deterministic heuristic baseline.

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

`search` reads the existing local analysis index. It does not rescan the folder or re-analyze images.

## 🔎 Explainability

`vibesorter explain` exposes the winning and runner-up vibes, score margin, ambiguity, selected secondary vibes, and the visual feature signals behind the deterministic classifier. The output is diagnostic rather than generated prose.

## 🔒 Safety

Detection, statistics, duplicate checks, search, proposals, reviews, and galleries are read-only with respect to source images. Actual filesystem changes still require explicit confirmation.

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
