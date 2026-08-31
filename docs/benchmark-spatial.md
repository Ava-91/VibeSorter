# Spatial feature benchmark

Spatial features reuse the existing 64x64 analysis image and add a fixed 2x2 region pass. Benchmark any classifier change against the same image set before and after spatial features.

Track:

- images/second
- median analysis latency
- peak memory
- classification accuracy
- per-vibe precision and recall
- ambiguous classification rate

A spatial feature change is considered useful only when quality improves enough to justify its small analysis overhead.
