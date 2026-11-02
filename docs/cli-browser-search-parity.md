# CLI and browser search parity

The CLI and browser search share the cached profile model, but they intentionally expose different query surfaces.

## Available in both interfaces

- Case-insensitive path/text search (the browser also searches serialized profile metadata).
- Media type, colors, temperature, saturation, brightness, and stored vibe filters.
- Multiple values within a multi-valued family are ORed; selected families are combined with AND.
- Secondary-vibe matching is available in the CLI; browser vibe filtering currently searches the stored score list as well.
- Both interfaces read the local analysis cache and do not rescan or modify source images.

## CLI-only filters

The CLI `vibesorter search` currently exposes additional review and numeric controls:

- `--min-score` and `--uncertain-margin` for score and top-two-margin review.
- `--max-text-likelihood`.
- Numeric minimum/maximum brightness, saturation, and contrast ranges.
- `--limit` for result count.

The browser does not currently expose these controls. Its controls focus on profile-family filtering, path/profile text search, sorting, and pagination.

## Interpretation

The CLI's uncertain-margin filter is a heuristic review queue, not a probability or correctness guarantee. Browser confidence display is also a heuristic score and should not be interpreted as calibrated probability.

## Validation boundary

Automated tests cover CLI parsing, cache filtering, and browser profile-filter behavior. Actual behavior against a user's private image library has not been independently validated as part of this repository change. Users should test against a small, non-sensitive sample library and report reproducible mismatches without sharing private images.

## Follow-up

This document records the current parity gap; it does not claim that browser controls have been added. A future UI change can add numeric ranges and uncertain-result review using the existing cache/query semantics, with regression tests for API filtering, pagination, and combined filters.
