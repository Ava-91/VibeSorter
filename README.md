# VibeSorter

> **Find the visual character of your image library.**
>
> VibeSorter is a local-first Python image organizer with a deterministic, feature-based heuristic classifier. It estimates independent visual attributes and overlapping aesthetic vibes, stores reusable results in SQLite, and separates safe discovery from explicit filesystem changes. It does not use a neural network or a remote AI service for its default predictions.

## What it classifies

VibeSorter keeps measurable features separate from semantic attributes. An image can be a **photograph + red + blue + cool + vibrant + bright + retro + playful** at the same time.

The canonical taxonomy is:

- **Media type:** photograph, illustration, screenshot, graphic, collage
- **Color:** red, orange, yellow, green, blue, purple, pink, neutral (multi-valued)
- **Temperature:** warm, cool, neutral
- **Saturation:** vibrant, muted, desaturated
- **Brightness:** bright, mid, dark
- **Vibes:** retro, dreamy, soft, moody, minimal, cozy, cinematic, playful, edgy, romantic (multi-valued)

These families are independent. Compound labels are not part of the canonical model. **Media-type prediction limitation:** the current heuristic automatically predicts only photograph, screenshot, or graphic. Illustration and collage are valid taxonomy values for stored or manually supplied profiles, but the default classifier does not yet predict them. Automatic support should only be added after it is evaluated on a representative human-labeled set. This is an intentional limitation, not a claim that illustration/collage detection is already implemented.

## How it works

The default classifier is a deterministic heuristic built from lightweight local image features: brightness, saturation, contrast, warm/cool balance, grayscale content, dark/light ratios, dominant colors, text likelihood, and spatial features. Its aesthetic labels are subjective approximations, not objective facts about an image. A confidence value is an internal score derived from heuristic strength and separation from alternatives; it is **not** a calibrated probability that the label is correct. Similar images can receive different labels, and unfamiliar styles or mixed scenes may be misclassified. Semantic classification stores an `ImageProfile` with per-attribute heuristic confidence and provenance. An optional learned classifier can be fitted from user-provided labels; it is a separate workflow and its quality depends on the quality and representativeness of those labels.

Repeated analysis persists raw features and structured profiles in the local SQLite cache at `.vibesorter/analysis.db`. Cached search and browser filtering operate on stored data without rescanning source images.

## Quick start

VibeSorter requires Python 3.11+.

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

### Desktop app

The desktop application uses **Tauri 2 + Rust** for the native shell while keeping the existing Python classifier, indexer, and SQLite browser as the source of truth.

For development, build the Tauri app from the repository root after installing the Tauri prerequisites for your platform:

```text
Rust toolchain
Python 3.11+
PyInstaller
Tauri 2 CLI
```

Build the Python sidecar first:

```powershell
python -m pip install -e .
python -m pip install pyinstaller
python scripts/build_sidecar.py
```

Then build the desktop application:

```powershell
cargo tauri build
```

The resulting installer/bundle is produced under `src-tauri/target/release/bundle/`. The GitHub Actions desktop workflow builds Windows, Linux, and macOS artifacts from the same sidecar + Tauri configuration.

The legacy `vibesorter desktop` command remains available as a browser compatibility mode for environments where the native app is not installed.

All interfaces are local-first. The native desktop shell does not upload source images to a third-party AI service.

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

Filter stored profile attributes (multiple `--color` or `--profile-vibe` values are ORed within that attribute family):

```bash
vibesorter search "path/to/photos" --media-type photograph --color blue --color red --temperature cool
vibesorter search "path/to/photos" --saturation-label muted --brightness-label dark --profile-vibe dreamy
vibesorter search "path/to/photos" --vibe dreamy --include-secondary-vibes
```

To review close calls, filter for a small gap between the top two vibe scores:

```bash
vibesorter search "path/to/photos" --uncertain-margin 0.08
```

This last option is a heuristic review signal, **not** a calibrated probability. Results still require human judgment.

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

Physical organization is a separate, explicit step. A folder plan chooses one primary attribute for folder names; secondary attributes remain metadata so multi-label images are not duplicated. Proposed moves are reviewable and read-only until the user explicitly confirms them. Existing destinations, missing sources, duplicate destinations, low-confidence classifications, and paths that escape the proposal's recorded source/output roots are blocked before mutation. Apply validates the whole accepted batch before moving any file; legacy reviewed proposals without a recorded source root must be regenerated. Applied moves can be rolled back.

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

Each successful move is first appended and flushed to a per-batch pending recovery journal. If a later move fails, VibeSorter attempts to restore completed moves in reverse order. The pending journal is removed after a complete rollback or after the final history record is committed; if rollback is incomplete, the journal is preserved and its path is included in the error so the remaining moves can be recovered manually. The final history file is committed atomically.

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

The CI workflow tests Python 3.11, 3.12, and 3.13 because the package declares `requires-python = ">=3.11"`.

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


### Browser query benchmark

Measure SQLite-backed profile filtering and pagination on a synthetic cached library (no image files or network required):

    python scripts/benchmark_browser_profiles.py --rows 50000

The benchmark reports filtered result count, page size, and elapsed query time. The browser applies supported profile filters, counts, ordering, and pagination in SQLite, and loads profile JSON only for the returned page.


### Verified-cache reindex benchmark

Measure directory discovery, first indexing, the content-verification pass, and a repeat index on generated local images:

    python scripts/benchmark_verified_reindex.py --files 250 --size 256 --workers 4

Content verification still hashes every candidate whose size and modification time match the cached identity. That full digest is necessary to detect same-size, same-mtime content changes; the optimization batches cache metadata lookups into one SQLite join and uses `hashlib.file_digest` to reduce Python-level hashing overhead.


Desktop lifecycle: the native shell binds browser access to loopback, rejects an occupied requested port before launching the sidecar, and requires an HTTP `/api/status` health response within five seconds. A failed startup is terminated and cleared; stale process events cannot overwrite a restarted backend, and active backend/analysis children are killed when the main window closes.


## Scanner and image-input contract

- Discovery uses extensions registered by the installed Pillow build. It is extension-based; decoding and corruption checks happen during analysis.
- Recursive scans include hidden user folders but prune VibeSorter-managed `.vibesorter` folders. Symlinked files and directories are excluded; directory symlinks are never followed.
- Directory traversal and permission errors are raised instead of silently returning a partial scan. Files that disappear, change, or become unreadable after discovery are handled as analysis failures; indexing removes stale cached analysis for a failed changed file.
- Unicode and long path components are handled through `pathlib`, subject to the underlying operating system's path limits.
- EXIF orientation is applied before analysis. Animated GIFs and other multi-frame formats are analyzed using their first frame only.
- Images exceeding Pillow's configured safe pixel limit are rejected before feature processing. Unsupported, corrupt, empty, or unreadable images produce a clear analysis error rather than a fabricated classification.


## Browser security and network exposure

The browser and labeling UI bind to loopback by default. Binding to a non-loopback interface is rejected unless `--allow-network` is explicitly supplied; opting in prints a warning because cached paths, metadata, and image bytes become reachable to other devices that can connect. Prefer a trusted private network and firewall rules, and stop the server when finished. This server is not intended to be an internet-facing service.

Requests are checked against the Host header; state-changing labeling requests require a same-origin `Origin` and `application/json` content type, with a bounded request body. Responses include anti-framing, MIME-sniffing, referrer, cache, and content-security headers. These checks reduce browser-based cross-origin abuse but are not a substitute for network isolation when `--allow-network` is used. The desktop shell restricts sidecar spawning to the fixed browser and index argument shapes and always requests a loopback browser host.


Rollback checks each recorded destination's SHA-256 before restoring it and refuses to overwrite occupied original paths. Missing files, modified contents, permission failures, and per-file restore errors are reported individually so other safe restores can continue. Corrupt history is rejected with a line number. If a rollback or apply fails, inspect the reported recovery-journal path and the source/destination paths before retrying; never delete a pending journal until the moved files have been reconciled.


## Classifier evaluation baseline

The evaluation command reports accuracy, per-vibe precision/recall/F1/support, a confusion matrix, ambiguity, and confidence calibration. Follow [the versioned human-labeling protocol](docs/evaluation-baseline-v1.md) before publishing a score. Model predictions are never ground truth; the repository does not claim a release-quality real-world benchmark until a representative human-labelled dataset and image manifest are committed.


## Classifier limitations

VibeSorter is a sorting aid, not an image-understanding authority. It does not infer personal identity, intent, location, or cultural context. The default classifier uses hand-designed visual features and deterministic scoring; it is not a trained deep-learning model. Vibe names such as `dreamy`, `cozy`, and `edgy` are inherently subjective. Scores and confidence are useful for ranking and deciding which items need human review, but they must not be presented as calibrated correctness probabilities. Evaluate changes only against a versioned, human-labelled holdout set; do not treat generated predictions as ground truth.


Version bumps must update the Python project/runtime and both Tauri version declarations together; see [the version synchronization checklist](docs/versioning.md). CI tests that these values remain identical.


## Desktop platform support

The supported OS/architecture matrix, known limitations, signing/notarization status, and install/upgrade/uninstall acceptance process are documented in [the desktop platform policy](docs/platform-support-and-signing.md). First-run setup, local data paths, backup/reset/uninstall, privacy, and troubleshooting are documented in [the data lifecycle guide](docs/data-lifecycle-and-troubleshooting.md). Intel macOS is not a v1.0 target, and current Windows/macOS release artifacts are unsigned/not notarized unless the release workflow is explicitly updated and verified.


Version bumps must update the Python project/runtime and both Tauri version declarations together; see [the version synchronization checklist](docs/versioning.md). CI tests that these values remain identical.
