# First-run, local data, privacy, and troubleshooting

## First run

1. Install Python 3.11 or newer and the supported VibeSorter build for your platform.
2. Start with a small copy of 5–20 images, not your only copy of a large library.
3. Run `vibesorter scan "path/to/test-images"` to list discoverable images without analyzing or moving them.
4. Run `vibesorter index "path/to/test-images"` to analyze supported images and build the local index.
5. Run `vibesorter search "path/to/test-images" --limit 20` or open the browser/desktop interface to inspect stored results.
6. Generate a proposal, review it, and use dry-run first. Applying accepted moves is a separate operation and requires explicit confirmation.
7. Verify results and practice rollback on the test copy before using a large or valuable library.

## What files VibeSorter creates

| Location | Purpose | Safe to delete? |
|---|---|---|
| `<selected-library>/.vibesorter/analysis.db` | SQLite index containing extracted features, vibe scores, and profile metadata | Usually rebuildable; deleting it discards cached analysis and requires re-indexing |
| `.vibesorter/history.jsonl` relative to the working directory by default, or the path passed with `--history` | Audit records and hashes for filesystem moves and rollback | **Do not treat as disposable** while you may need rollback or an audit trail |
| `src-tauri/binaries/` and build output folders | Developer/build artifacts, not user-library data | Build artifacts may be regenerated; this is not the app's user-data directory |

The analysis database is stored inside the selected library. The default history path is relative to the process's current working directory, not automatically the selected library. For predictable record keeping, pass an explicit `--history` path to `apply`, `rollback`, and `history`, and keep that file backed up with the library.

## Backup, reset, and uninstall

- **Before moving files:** keep a separate backup of the original images. The operation journal helps recovery but is not a substitute for a backup.
- **Back up VibeSorter state:** stop the desktop/browser process first, then copy the selected library's `.vibesorter` directory and the configured history JSONL file to a separate location.
- **Reset cached analysis:** after backing it up, close VibeSorter and remove only the relevant `analysis.db`. The next index run rebuilds derived analysis. Do not remove `history.jsonl` if rollback or audit history matters.
- **Uninstall:** uninstalling the application does not intentionally delete your original image library or its `.vibesorter` directory. Inspect those paths yourself if you want to remove application-created data.
- **After a feature-version change:** old derived cache entries may be invalidated and recomputed. This is expected and does not modify the source images.

## Privacy and network behavior

The default analysis is local and feature-based; it does not send source images to a remote AI service. The SQLite database contains file paths and derived visual metadata, so treat it as private even though it does not contain a copy of every source image.

The browser and labeling servers bind to loopback by default. Do not expose them to the internet. The explicit `--allow-network` option can make cached paths, metadata, and image bytes reachable by other devices that can connect. Use it only on a trusted private network with appropriate firewall rules, and stop the server when finished. The native desktop shell is designed to communicate with a loopback sidecar.

## Supported formats and platform limitations

VibeSorter discovers file extensions registered by the installed Pillow build and validates actual decoding during analysis. Unsupported, corrupt, empty, unreadable, or oversized images may be skipped with an error; a discovered filename is not proof that its contents can be decoded.

The supported desktop build targets and signing/notarization limitations are listed in [Desktop platform support and signing](platform-support-and-signing.md). Current artifacts are not signed/notarized unless the release notes explicitly say otherwise.

## Troubleshooting

### No images found
- Confirm the folder exists and is a directory.
- Check whether the installed Pillow build supports the file format.
- Symlinked files/directories and VibeSorter-managed `.vibesorter` directories are intentionally excluded.
- Check read permissions. Traversal errors are surfaced rather than silently treated as a complete scan.

### Search says no cache exists
Run `vibesorter index "path/to/library"` first. Search is read-only and does not perform a new scan or analysis.

### The browser shows an empty or unreadable database
Confirm that the browser is pointed at the intended `<library>/.vibesorter/analysis.db`. A missing database, a valid empty database, and an incompatible/unreadable database are different states; read the status message before resetting anything.

### Desktop startup fails or results do not appear
- Confirm the app is installed from a complete artifact for your OS and architecture.
- Restart once and check whether the sidecar starts and the status view reports a healthy backend.
- Preserve logs and the library's database/history before attempting a reset.
- If the problem repeats, file a bug report with the version, OS/architecture, exact reproduction steps, relevant redacted logs, and whether it reproduces on a small test library.

### Apply or rollback reports a conflict
Do not manually overwrite the conflicting path. The safety checks may be protecting an existing file or a destination whose content hash changed. Preserve the history/journal, inspect both paths, and make a backup before deciding how to resolve the conflict.

## Reporting bugs safely

Do not upload private image libraries or screenshots that expose sensitive filenames. Provide the smallest reproducible example possible, redact user names and absolute paths from logs, and say whether a synthetic test image reproduces the issue.
