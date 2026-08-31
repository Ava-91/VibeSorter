# Spatial features

VibeSorter extracts a small 2x2 grid of regional brightness, saturation, warm-color ratio, and cool-color ratio values in addition to global image features.

The grid is computed from the same 64x64 in-memory image used by the existing analyzer, so the feature is local and intentionally lightweight. A center-vs-edge delta is also retained to distinguish images whose visual emphasis is concentrated near the center from images whose edges dominate.

Spatial features are signals, not object recognition. They help the classifier distinguish otherwise similar global palettes without attempting to understand what an image contains.
