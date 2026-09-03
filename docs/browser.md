# Interactive browser

VibeSorter includes a local browser for reviewing cached analysis without re-running the classifier.

## Run

```bash
vibesorter browser
```

The server binds to `127.0.0.1` by default. Open the printed local URL in a browser.

## Data flow

```text
SQLite analysis index
        ↓
/api/vibes ──────────────┐
        ↓                 │
summary/navigation       │
        │                 │
/api/images?page=N&limit=48
        ↓
small result page
        ↓
thumbnail grid
        ↓
/api/image?path=...
```

The browser reads the existing SQLite analysis index. Switching pages, vibes, or text filters does not rescan or re-analyze the image library.

## Vibe navigation

The sidebar lists primary vibes with result counts. Selecting a vibe changes the current image query and keeps pagination bounded. Average confidence is available from the summary API for future summary views.

## Pagination and loading

- API pages default to 48 results and cap requests at 120.
- Results are ordered by path for stable pagination.
- The UI loads more results explicitly instead of rendering the whole library at once.
- Image elements use native browser lazy loading and asynchronous decoding.
- Thumbnails are served from the original local image paths only when that path is present in the analysis index.
- Missing or unreadable images are shown as placeholders rather than breaking the whole grid.

## Privacy

The browser is local-first. It does not upload images to a cloud service. The image endpoint is intentionally limited to files already referenced by the local analysis database.
