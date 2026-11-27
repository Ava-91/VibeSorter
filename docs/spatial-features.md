# Image feature measurements (version 3)

All image analysis uses a bounded 64×64 thumbnail. EXIF orientation is applied first. RGBA images retain their original RGB values for partially transparent artwork (preserving existing palette behavior), while fully transparent pixels are neutralized so hidden RGB values cannot distort visible-color measurements. `alpha_coverage` separately records mean source opacity.

## Distributions

`luminance_percentiles` and `saturation_percentiles` contain P10, P25, P50, P75 and P90, normalized to 0–1 and linearly interpolated between sorted thumbnail samples. They retain spread and skew that a single mean cannot describe. They are summaries, not a full histogram.

## Palette and complexity

The palette retains the most frequent quantized RGB bins and, when it is meaningfully present (at least 1% of thumbnail pixels), promotes a vivid accent bin so a small saturated region is less likely to disappear behind a neutral background. Palette proportions refer to thumbnail pixels and need not sum to one after accent promotion.

`edge_density` is the fraction of horizontal/vertical neighboring luminance pairs whose absolute difference is at least 24 on the 0–255 scale. `color_diversity` is the number of distinct 16-step RGB bins divided by 32 and capped at 1. These inexpensive proxies describe local visual variation; they do not identify objects or measure artistic quality.

## Spatial information and resource bounds

The existing 2×2 regional summaries and center-versus-outer deltas are retained. All new calculations operate on the same 64×64 thumbnail (at most 4,096 samples); no full-resolution pixel list is created. Percentile sorting is bounded to 4,096 values. Feature version 3 invalidates stale SQLite feature records so old cached measurements are not silently interpreted as the new schema.

## Benchmarking

Run `python scripts/benchmark_features.py` on the same machine and image corpus before and after a feature change. The script reports median and p95 latency, images/second, and Python-tracked peak allocation for 256px, 1024px and 4096px images. Pillow may allocate native memory not visible to tracemalloc, so treat that number as a lower-bound indicator. Keep the baseline output beside the post-change output; do not compare runs from different machines or claim a speedup from synthetic fixtures alone.
