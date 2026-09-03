# Incremental library indexing

Use `vibesorter index` to persist local image analysis into the SQLite cache used by the browser and search commands.

## Run

```bash
vibesorter index "E:\\Ava files\\Pictures\\Billie Eilish"
```

The command recursively discovers supported images and writes the cache to:

```text
<folder>/.vibesorter/analysis.db
```

The cache is local to the selected library. Images are never uploaded.

## Incremental behavior

On the first run, every valid image is analyzed. On later runs, an image is reused when its cached `size` and `mtime_ns` still match the file on disk. New or changed images are analyzed again.

Entries for files that no longer exist are removed from the cache after each run.

## Options

- `--no-recursive` scans only the selected folder.
- `--workers N` controls analysis concurrency.
- `--json` emits machine-readable run statistics.

The output reports the total discovered images, newly analyzed images, reused cache entries, skipped analysis failures, removed stale entries, and database path.

## Browser

After indexing a library, launch its browser with the generated database:

```bash
vibesorter browser --db "E:\\Ava files\\Pictures\\Billie Eilish\\.vibesorter\\analysis.db"
```

Filtering, pagination, and image details use this cached data without re-running analysis.
