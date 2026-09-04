# VibeSorter

> **Find the visual character of your image library.**
>
> VibeSorter is a local-first Python CLI that analyzes images using independent visual attributes and overlapping aesthetic vibes.

## What it classifies

VibeSorter keeps measurable features separate from semantic attributes. An image can be a **photograph + red + blue + cool + vibrant + bright + retro + playful** at the same time.

The canonical taxonomy is:

- **Media type:** photograph, illustration, screenshot, graphic, collage
- **Color:** red, orange, yellow, green, blue, purple, pink, neutral (multi-valued)
- **Temperature:** warm, cool, neutral
- **Saturation:** vibrant, muted, desaturated
- **Brightness:** bright, mid, dark
- **Vibes:** retro, dreamy, soft, moody, minimal, cozy, cinematic, playful, edgy, romantic (multi-valued)

These families are independent. Compound labels are not part of the canonical model.

## How it works

The detector uses lightweight local image features including brightness, saturation, contrast, warm/cool balance, grayscale content, dark/light ratios, dominant colors, text likelihood, and spatial features. Semantic classification stores an `ImageProfile` with confidence and provenance for each attribute.

Repeated analysis persists raw features and structured profiles in the local SQLite `.vibesorter/analysis.db` cache. Cached search and browser filtering operate on stored data without rescanning source images.

## Search and organization

Search combines independent attributes instead of requiring a compound category. Multiple values in a multi-valued family are supported, while different families can be combined with AND semantics.

Physical organization is a separate, explicit step. A folder plan chooses one primary attribute for folder names; secondary attributes remain metadata so multi-label images are not duplicated. Proposed moves are reviewable and read-only until the user explicitly confirms them. Existing destinations, missing sources, duplicate destinations, and low-confidence classifications are blocked before mutation, and applied moves can be rolled back.

## Legacy data

The pre-v2 compound vocabulary is retired from the canonical taxonomy. Historical records containing those labels are treated as legacy/unmigrated data rather than being silently guessed into new attributes. New `ImageProfile` instances accept only canonical family values, so compound labels cannot re-enter the semantic model.

## Installation

Python 3.10+ is required.

```bash
python -m pip install -e .
```

## CLI

```bash
vibesorter scan "path/to/photos"
vibesorter analyze "path/to/photo.jpg"
vibesorter stats "path/to/photos"
vibesorter search "path/to/photos" --min-score 0.80 --path "billie"
vibesorter search "path/to/photos" --min-brightness 0.65 --max-saturation 0.75 --limit 50
```

## Python API

```python
from vibesorter import analyze_library

for result in analyze_library("path/to/photos"):
    print(result.path, result.best.name, result.best.score, result.cached)
```

Structured classification is available directly:

```python
from vibesorter.classifier import classify_profile
from vibesorter.features import extract_features

profile = classify_profile(extract_features("path/to/photo.jpg"))
print(profile.to_dict())
```

## Safety and privacy

Analysis, search, statistics, duplicate checks, proposals, reviews, and browser views are local and read-only with respect to the source library. Filesystem changes require explicit confirmation, and the organization layer provides rollback support.

VibeSorter is local-first: source images are not uploaded to a third-party AI service by the project.

## Development status

The multidimensional taxonomy migration is complete. The canonical model is stable and protected by regression tests covering schema validation, serialization, multi-valued attributes, per-attribute confidence/provenance, contradictory combinations such as Red + Cool, SQLite persistence, browser filtering, folder planning, filesystem apply/rollback, and rejection of retired compound labels.

The project can continue to improve classifier quality and interfaces without changing the semantic taxonomy contract.

## Tech

- Python
- Pillow
- SQLite
- Deterministic local feature extraction and classification
- Offline evaluation and learned-classifier comparison
- Local browser UI

## License

See [LICENSE](LICENSE).
