# Multi-vibe classification

Aesthetic categories overlap. VibeSorter keeps the full ranked score list and derives a selected-vibe set from a score threshold and winner margin.

The strongest category remains `best` for compatibility with existing proposals and reports. Secondary categories are available through `AnalysisResult.vibes`, cached scores, search, and explanation output.

This makes ambiguity explicit without forcing every interface to become multi-label immediately.
