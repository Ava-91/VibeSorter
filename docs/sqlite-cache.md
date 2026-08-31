# SQLite analysis cache

The primary persistent analysis index is now `.vibesorter/analysis.db`.

The schema keeps one row per image with file identity, serialized features, and vibe scores. SQLite gives VibeSorter transactional writes and a queryable persistent store without adding a third-party dependency.

If a legacy `.vibesorter/analysis.json` exists, the SQLite cache imports its entries on first initialization. Existing source images are still revalidated by size and nanosecond modification time before cached results are returned.

The JSON file is treated as migration input, not the primary index.
