# VibeSorter

A local, lightweight image organizer that will eventually sort photos by visual aesthetics, colors, moods, and vibes — without sending images to a cloud AI service.

## Phase 1

The project starts as a terminal-first Python application. The first step is deliberately simple: discover images in a folder without changing anything.

### Supported images

- JPEG / JPG
- PNG
- WebP
- BMP
- GIF
- TIFF

The scanner searches subfolders by default and treats extensions case-insensitively.

## Development

Python 3.10+ is required.

```bash
python -m pip install -e .
vibesorter scan "path/to/your/photos"
```

To scan only the selected folder:

```bash
vibesorter scan "path/to/your/photos" --no-recursive
```

The `scan` command is read-only: it discovers and prints image paths but does not move, rename, delete, or edit files.

## Roadmap

1. Folder discovery and CLI foundation
2. Local visual feature extraction
3. Vibe classification
4. Preview proposed groups
5. User-confirmed folder creation and sorting
6. Desktop application
