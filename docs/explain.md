# Explaining a classification

The explanation layer exposes the information behind a prediction:

- winning vibe
- confidence heuristic
- score margin over the runner-up
- ambiguity flag
- full ranked candidate scores
- extracted visual features

The planned CLI surface is:

```bash
vibesorter explain image.jpg
vibesorter explain image.jpg --json
```

It is read-only and exists for debugging and trust, not semantic image recognition.
