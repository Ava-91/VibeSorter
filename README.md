# VibeSorter

> **Find the visual character of your image library.**
>
> VibeSorter is a local-first Python image organizer that analyzes independent visual attributes, overlapping aesthetic vibes, and confidence signals. It keeps analysis local, stores reusable results in SQLite, and separates safe discovery from explicit filesystem changes.

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

Repeated analysis persists raw features and structured profiles in the local SQLite cache at `.vibesorter/analysis.db`. Cached search and browser filtering operate on stored data without rescanning source images.

## Quick start

VibeSorter requires Python 3.10+.

### Windows — Git Bash

```bash
git clone https://github.com/Ava-91/VibeSorter.git
cd VibeSorter
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Windows — Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Windows — PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### macOS / Linux

```bash
git clone https://github.com/Ava-91/VibeSorter.git
cd VibeSorter
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Verify the installation:

```bash
vibesorter --help
vibesorter --version
```

## Interfaces

VibeSorter has three entry points:

### CLI

The CLI is the main workflow interface:

```bash
vibesorter --help
```

### Browser UI

Browse the cached SQLite analysis locally:

```bash
vibesorter-browser
```

Or choose the database, host, and port explicitly:

```bash
vibesorter browser --db "path/to/photos/.vibesorter/analysis.db" --host 127.0.0.1 --port 8765
```

### Desktop shell

Launch the local desktop shell around the browser interface:

```bash
vibesorter-desktop
```

Or:

```bash
vibesorter desktop --db "path/to/photos/.vibesorter/analysis.db" --port 8765
```

All interfaces are local-first. They do not upload source images to a third-party AI service.

## Full CLI workflow

For a first run, use a small test folder instead of your entire library. A folder containing 5–20 images is enough to validate the workflow.

### 1. Discover images

```bash
vibesorter scan "path/to/photos"
```

`scan` is read-only. It lists supported image files and does not analyze, move, rename, copy, or delete them.

### 2. Analyze one image

```bash
vibesorter analyze "path/to/photo.jpg"
```

This prints the best vibe, confidence, text/screenshot likelihood, and the full vibe ranking.

### 3. Build or refresh the local cache

```bash
vibesorter index "path/to/photos"
```

`index` is the preferred incremental library-analysis command. It stores reusable results in:

```text
path/to/photos/.vibesorter/analysis.db
```

The legacy `preview`, `stats`, and `propose` commands also persist the analyses they perform to the same cache.

### 4. Inspect statistics

```bash
vibesorter stats "path/to/photos"
```

You can request JSON output:

```bash
vibesorter stats "path/to/photos" --json
```

### 5. Search the cache

Search is fast and read-only; it does not re-analyze source images.

```bash
vibesorter search "path/to/photos" --limit 20
```

Filter by the **best** vibe:

```bash
vibesorter search "path/to/photos" --vibe minimal
vibesorter search "path/to/photos" --vibe cozy --min-score 0.60
```

Filter by filename/path and visual measurements:

```bash
vibesorter search "path/to/photos" --path "billie"
vibesorter search "path/to/photos" --min-brightness 0.65 --max-saturation 0.75 --limit 50
```

Search never modifies source images.

### 6. Check duplicates

```bash
vibesorter duplicates "path/to/photos"
```

This reports exact duplicates and perceptual near-duplicate pairs without changing files.

### 7. Create an organization proposal

```bash
vibesorter propose "path/to/photos" --output proposal.json
```

This creates a deterministic plan. **Nothing is moved yet.**

You can choose a different destination root:

```bash
vibesorter propose "path/to/photos" --output-root "VibeSorted" --output proposal.json
```

### 8. Review the proposal

Accept specific operation IDs:

```bash
vibesorter review proposal.json --accept 1,3-5 --output proposal-reviewed.json
```

Accept every operation for a vibe:

```bash
vibesorter review proposal.json --accept-vibe minimal --accept-vibe cozy
```

Reviewing is still read-only.

### 9. Preview filesystem changes

Before a real apply, use a dry run:

```bash
vibesorter apply proposal-reviewed.json --dry-run
```

A dry run never moves files.

### 10. Apply the reviewed moves

Real filesystem changes require explicit confirmation:

```bash
vibesorter apply proposal-reviewed.json --confirm
```

Successful applies create an auditable history record and print the generated **batch ID**. Keep that ID if you may want to roll the operation back.

### 11. Inspect history

```bash
vibesorter history
```

Machine-readable history:

```bash
vibesorter history --json
```

You can choose another history file with `--history` on `apply`, `history`, and `rollback`.

### 12. Preview a rollback

Use the batch ID printed by `apply`:

```bash
vibesorter rollback BATCH_ID --dry-run
```

Only after checking the planned restores should you perform them:

```bash
vibesorter rollback BATCH_ID --confirm
```

Rollback verifies the recorded file hash before restoring a file and refuses to overwrite an occupied source path or changed destination.

## Search and organization

Search combines independent attributes instead of requiring a compound category. Multiple values in a multi-valued family are supported, while different families can be combined with AND semantics.

Physical organization is a separate, explicit step. A folder plan chooses one primary attribute for folder names; secondary attributes remain metadata so multi-label images are not duplicated. Proposed moves are reviewable and read-only until the user explicitly confirms them. Existing destinations, missing sources, duplicate destinations, and low-confidence classifications are blocked before mutation, and applied moves can be rolled back.

## Python API

Analyze a library:

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

Analysis, search, statistics, duplicate checks, proposals, reviews, and browser views are local and read-only with respect to the source library. Filesystem changes require explicit confirmation.

Apply history is written atomically. If durable history cannot be committed after a move, VibeSorter attempts to restore the just-moved files instead of silently leaving filesystem changes without an audit record.

VibeSorter is local-first: source images are not uploaded to a third-party AI service by the project.

## Legacy data

The pre-v2 compound vocabulary is retired from the canonical taxonomy. Historical records containing those labels are treated as legacy/unmigrated data rather than being silently guessed into new attributes. New `ImageProfile` instances accept only canonical family values, so compound labels cannot re-enter the semantic model.

## Development

Install development dependencies in the virtual environment:

```bash
python -m pip install -e ".[dev]"
```

Run the same checks used by CI:

```bash
ruff check .
pytest -q
```

The CI workflow tests Python 3.10, 3.11, 3.12, and 3.13 because the package declares `requires-python = ">=3.10"`.

When changing the classifier or taxonomy, add regression tests for the changed contract. When changing filesystem operations, test dry-run, confirmation, history, conflict handling, and rollback behavior.

## Development status

The multidimensional taxonomy migration is complete. The canonical model is stable and protected by regression tests covering schema validation, serialization, multi-valued attributes, per-attribute confidence/provenance, contradictory combinations such as Red + Cool, SQLite persistence, browser filtering, folder planning, filesystem apply/rollback, and rejection of retired compound labels.

## Tech

- Python
- Pillow
- SQLite
- Deterministic local feature extraction and classification
- Offline evaluation and learned-classifier comparison
- Local browser UI

## License

See [LICENSE](LICENSE).
