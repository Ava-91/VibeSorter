# `vibesorter explain`

`explain` is intended to answer *why* an image received its classification rather than presenting a single mysterious score.

The explanation includes:

- primary winner and raw score
- runner-up scores and winner margin
- ambiguity/uncertainty information
- selected secondary vibes
- the main visual feature signals used by the deterministic classifier
- weighted score contributions for every vibe
- full extracted feature data in JSON mode

The feature signals are measurements, not generated prose. VibeSorter does not claim to recognize objects or infer semantic meaning from them.

## Score contributions

The non-JSON output includes a `Score contributions` section. Each line is the weighted contribution of one classifier input to a vibe's score. For example, `low_saturation` is the contribution produced by the saturation term in the corresponding vibe formula.

The contribution values for a vibe sum to its raw score (within rounding). They describe the deterministic scoring formula; they are not probabilities and should not be interpreted as independent evidence.

This makes ambiguous classifications inspectable. If a surprising vibe wins, compare its largest contributions with the feature signals above to identify which inputs are driving the result.

## JSON output

`vibesorter explain --json IMAGE` returns the same explanation as machine-readable JSON. The nested feature object's `path` is serialized as a string so the command is safe to pipe to other tools.

The JSON also contains `score_contributions`, keyed by vibe name, with weighted feature contributions for each score.
