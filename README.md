# VibeSorter

A local, lightweight image organizer that detects visual aesthetics, colors, moods, and vibes — without sending images to a cloud AI service.

## Current phase: vibe detection

VibeSorter is deliberately focused on **visual vibe detection** for now. It does not try to understand text, OCR screenshots, or identify the subject of an image. Text-heavy images can be left for a future phase.

The detector uses lightweight local image features such as color, brightness, saturation, contrast, warm/cool balance, grayscale content, and dark/light ratios.

### Vibe categories

- Retro Blue
- Red / Warm
- Green & Black
- Black & White
- Soft / Pastel
- Dark / Moody
- Bright / Colorful

### Supported images

- JPEG / JPG
- PNG
- WebP
- BMP
- GIF
- TIFF

The scanner searches subfolders by default and treats extensions case-insensitively.

## CLI

Python 3.10+ is required.

```bash
python -m pip install -e .
```

Discover images without analyzing them:

```bash
vibesorter scan "path/to/your/photos"
```

Detect vibes for a whole folder:

```bash
vibesorter preview "path/to/your/photos"
```

Analyze one image and see its complete ranking:

```bash
vibesorter analyze "path/to/photo.jpg"
```

Get a compact vibe-count report:

```bash
vibesorter stats "path/to/your/photos"
```

Useful options for `preview` and `stats`:

```bash
vibesorter preview "path/to/photos" --workers 8
vibesorter preview "path/to/photos" --vibe "Dark / Moody"
vibesorter preview "path/to/photos" --min-score 0.70
vibesorter preview "path/to/photos" --top 10
vibesorter stats "path/to/photos" --json
```

`--json` is also available on `analyze`. JSON output makes the detector easier to integrate into scripts later.

All commands are read-only: VibeSorter does not move, rename, delete, or edit your images.

## Development

The project is terminal-first and intentionally local. The analysis pipeline uses Pillow and concurrent workers so large image libraries can be processed without sending images anywhere.

## Roadmap

1. Folder discovery and CLI foundation
2. Local visual feature extraction
3. Vibe classification
4. Better text/screenshot awareness
5. Preview proposed groups
6. User-confirmed folder creation and sorting
7. Desktop application
