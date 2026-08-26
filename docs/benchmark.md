# Benchmarking

The benchmark engine measures end-to-end local image analysis without moving or modifying source files.

```python
from vibesorter.benchmark import benchmark

result = benchmark("./photos", repeats=3)
print(result.to_dict())
```

Metrics include image count, repeats, elapsed time, throughput, and milliseconds per analyzed image. Repeat counts make it possible to compare changes while reducing one-off timing noise.
