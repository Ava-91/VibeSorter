# Confidence-aware labels and personal corrections

## Heuristic evidence is not probability

Vibe scores are raw normalized heuristic evidence. The margin is the difference between the leading and runner-up raw scores. The separate ranking signal combines the top score and its margin; it is not a calibrated probability or a guarantee of correctness.

The only confidence policy is `DEFAULT_CONFIDENCE_THRESHOLDS` in `vibesorter.vibes`:

| Category | Minimum top score | Minimum margin | Behavior |
| --- | ---: | ---: | --- |
| Strong | 0.72 | 0.16 | Assign the leading label |
| Possible | 0.55 | 0.08 | Assign the leading label, clearly marked possible |
| Uncertain | Below either possible boundary | — | Abstain; do not assign a vibe |

The boundaries are inclusive. When the image has no usable scores, the result is uncertain. Each decision includes a concise reason. Raw scores remain available for inspection and evaluation even when the label is withheld.

The CLI `analyze` and `explain` commands, the browser, stored profiles, search and proposal workflow use the same policy. Uncertain images are grouped under `Needs review` rather than being silently assigned the top-ranked vibe.

## Local personal corrections

The browser detail view lets a user mark the top-ranked suggestion correct, incorrect or partially correct. A partial correction can nominate a different canonical vibe. Corrections are stored in the library's local SQLite database in `personal_corrections`, keyed by SHA-256 content identity rather than path alone. Reindexing or copying identical bytes therefore does not create duplicate feedback rows; changed content receives a new identity.

Personal preferences are computed separately from the global classifier scores. Each stored correction contributes a small vote, and the resulting additive ranking adjustment is capped to ±0.05. Raw feature scores, global classifier metrics and cached profiles are not rewritten. The browser marks personalized rankings explicitly.

The browser's Personal preferences panel and the CLI command `vibesorter corrections` inspect the stored records. Use `vibesorter corrections --undo` to restore the previous correction state, or `vibesorter corrections --clear` to remove all records and undo history. These actions never modify image files, send telemetry, or upload images.
